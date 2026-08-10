#!/usr/bin/env python3
"""
capture_campaign_c.py — Unattended serial capture for the two-unit comparison.

Campaign C exists to answer one question the paper currently asserts rather
than measures: does a second physical RP2040 produce the same timings as the
first? It is a NEW capture at n=1000, not a re-run of Campaign A. Campaign A
(n=30 / n=100) remains the published dataset and is not touched.

Why this script rather than parse_serial.py
-------------------------------------------
parse_serial.py streams until the operator presses Ctrl+C. That is fine for a
20-second capture and wrong for an hour-long unattended one: there is no
completion signal, no way to tell a finished run from a crashed one, and a
dropped USB row is invisible. This script instead:

  * stops by itself when the firmware prints its completion marker;
  * knows how many rows to expect and fails loudly if any are missing;
  * records the board's unique ID and measured clk_sys from the capture
    header, so a mislabelled board cannot silently corrupt the comparison;
  * writes a JSON sidecar with the provenance the paper will need to cite;
  * saves the raw serial log verbatim alongside the parsed CSV.

Usage
-----
    python scripts/capture_campaign_c.py --port /dev/ttyACM0 --board 1 \
        --firmware mlkem

    # list candidate ports and exit
    python scripts/capture_campaign_c.py --list-ports

Run once per firmware image per board. Output lands in
results/campaign_c/board<N>/.
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.exit("pyserial not installed. Run: pip install pyserial")


# Expected row counts per firmware image, as a function of the sample counts
# the firmware was built with. Used to detect dropped USB rows: a capture that
# is short by even one row is not silently accepted.
#
# Structure: firmware -> list of (algorithm, operation, security_level, kind)
# where kind selects which sample count applies.
EXPECTED = {
    "mlkem": [
        ("ML-KEM", op, lvl, "det")
        for lvl in (512, 768, 1024)
        for op in ("keygen", "encaps", "decaps")
    ],
    "mldsa": (
        [("ML-DSA", op, lvl, "det")
         for lvl in (44, 65, 87)
         for op in ("keygen", "verify")]
        + [("ML-DSA", "sign", lvl, "sign") for lvl in (44, 65, 87)]
    ),
    "classical": [
        ("ECDH-P256", "key_agreement", 256, "det"),
        ("ECDSA-P256", "keygen", 256, "det"),
        ("ECDSA-P256", "sign", 256, "det"),
        ("ECDSA-P256", "verify", 256, "det"),
        ("RSA-2048", "encrypt", 2048, "det"),
        ("RSA-2048", "decrypt", 2048, "rsa_dec"),
        ("RSA-2048", "keygen", 2048, "rsa_keygen"),
    ],
    "rng": [("randombytes", "generate", sz, "rng") for sz in (1, 32, 64)],
}

DONE_MARKER = re.compile(r"^#\s*===.*complete\s*===", re.I)
BOARD_ID_RE = re.compile(r"^#\s*Board unique ID:\s*([0-9A-Fa-f]+)")
CLK_RE = re.compile(r"^#\s*CPU:\s*(\d+)\s*Hz")
BUILD_RE = re.compile(r"^#\s*Build:\s*(.+)")
SUMMARY_RE = re.compile(r"^#\s*SUMMARY\s+(\S+)\s+(\S+)\s+(\d+):")


def parse_args():
    p = argparse.ArgumentParser(
        description="Unattended Campaign C capture (two-unit comparison)")
    p.add_argument("--list-ports", action="store_true",
                   help="List serial ports and exit")
    p.add_argument("--port", help="Serial port, e.g. /dev/ttyACM0 or COM4")
    p.add_argument("--board", type=int, choices=(1, 2),
                   help="Which physical board this is (1 = original, 2 = new)")
    p.add_argument("--firmware", choices=sorted(EXPECTED),
                   help="Which firmware image is flashed")
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--n-det", type=int, default=1000,
                   help="Deterministic-op sample count the firmware was built with")
    p.add_argument("--n-sign", type=int, default=1000,
                   help="ML-DSA signing sample count")
    p.add_argument("--n-rsa-dec", type=int, default=100)
    p.add_argument("--n-rsa-keygen", type=int, default=3)
    p.add_argument("--n-rng", type=int, default=2000)
    p.add_argument("--outdir", default=None,
                   help="Override output directory")
    p.add_argument("--idle-timeout", type=float, default=600.0,
                   help="Abort if no line arrives for this many seconds "
                        "(default 600; RSA-2048 keygen alone can take ~4 min "
                        "per sample, so do not set this too low)")
    return p.parse_args()


def show_ports():
    ports = list(list_ports.comports())
    if not ports:
        print("No serial ports found. Is the board plugged in and running "
              "firmware (not in BOOTSEL mode)?")
        return
    for p in ports:
        print(f"  {p.device:20s} {p.description}")


def expected_counts(args):
    per_kind = {
        "det": args.n_det,
        "sign": args.n_sign,
        "rsa_dec": args.n_rsa_dec,
        "rsa_keygen": args.n_rsa_keygen,
        "rng": args.n_rng,
    }
    out = {}
    for algo, op, lvl, kind in EXPECTED[args.firmware]:
        out[(algo, op, str(lvl))] = per_kind[kind]
    return out


def main():
    args = parse_args()

    if args.list_ports:
        show_ports()
        return 0

    missing = [f"--{k}" for k in ("port", "board", "firmware")
               if getattr(args, k) is None]
    if missing:
        sys.exit(f"Missing required argument(s): {', '.join(missing)}\n"
                 f"Run with --list-ports to find the serial port.")

    outdir = args.outdir or os.path.join(
        "results", "campaign_c", f"board{args.board}")
    os.makedirs(outdir, exist_ok=True)
    csv_path = os.path.join(outdir, f"{args.firmware}.csv")
    log_path = os.path.join(outdir, f"{args.firmware}_serial.log")
    meta_path = os.path.join(outdir, f"{args.firmware}_meta.json")

    want = expected_counts(args)
    total_expected = sum(want.values())

    print(f"Campaign C capture — board {args.board}, firmware {args.firmware}")
    print(f"Port:     {args.port} @ {args.baud}")
    print(f"Expect:   {total_expected} data rows across {len(want)} operations")
    print(f"Output:   {csv_path}")
    print("Waiting for the board to start printing. If nothing appears, press")
    print("the board's RESET (or unplug/replug) — the firmware waits for USB.\n")

    try:
        ser = serial.Serial(args.port, args.baud, timeout=1.0)
    except serial.SerialException as e:
        sys.exit(f"ERROR: could not open {args.port}: {e}")

    rows = []
    header = None
    meta = {
        "campaign": "C",
        "board": args.board,
        "firmware": args.firmware,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "sample_counts": {
            "deterministic": args.n_det, "sign": args.n_sign,
            "rsa_decrypt": args.n_rsa_dec, "rsa_keygen": args.n_rsa_keygen,
            "rng": args.n_rng,
        },
        "board_unique_id": None,
        "clk_sys_hz": None,
        "firmware_build": None,
        "summaries": [],
    }
    seen = {}
    t0 = time.time()
    last_line = time.time()
    done = False

    with open(log_path, "w", encoding="utf-8") as logf:
        try:
            while not done:
                raw = ser.readline()
                if not raw:
                    if time.time() - last_line > args.idle_timeout:
                        print(f"\nERROR: no output for {args.idle_timeout:.0f}s "
                              f"— board may have crashed or reset.")
                        break
                    continue
                last_line = time.time()

                try:
                    line = raw.decode("utf-8", errors="replace").strip()
                except Exception:
                    continue
                if not line:
                    continue

                logf.write(line + "\n")
                logf.flush()

                if line.startswith("#"):
                    m = BOARD_ID_RE.match(line)
                    if m:
                        meta["board_unique_id"] = m.group(1).upper()
                        print(f"  board unique ID: {m.group(1).upper()}")
                    m = CLK_RE.match(line)
                    if m:
                        meta["clk_sys_hz"] = int(m.group(1))
                        print(f"  clk_sys: {int(m.group(1)):,} Hz")
                    m = BUILD_RE.match(line)
                    if m:
                        meta["firmware_build"] = m.group(1).strip()
                    m = SUMMARY_RE.match(line)
                    if m:
                        meta["summaries"].append(line.lstrip("# ").strip())
                        print("  " + line.lstrip("# ").strip())
                    if "WARNING" in line or "ERROR" in line:
                        print("  !! " + line)
                    if DONE_MARKER.match(line):
                        done = True
                    continue

                if line.startswith("algorithm,"):
                    if header is None:
                        header = line.split(",")
                    continue

                parts = line.split(",")
                if len(parts) >= 5:
                    rows.append(parts[:5])
                    key = (parts[0], parts[1], parts[2])
                    seen[key] = seen.get(key, 0) + 1
                    if len(rows) % 500 == 0:
                        el = time.time() - t0
                        pct = 100.0 * len(rows) / total_expected
                        rate = len(rows) / el if el > 0 else 0
                        eta = (total_expected - len(rows)) / rate if rate else 0
                        print(f"  {len(rows)}/{total_expected} rows "
                              f"({pct:.0f}%) — ETA {eta/60:.0f} min")

        except KeyboardInterrupt:
            print("\nInterrupted by user — writing what was captured.")
        finally:
            ser.close()

    meta["finished_utc"] = datetime.now(timezone.utc).isoformat()
    meta["elapsed_s"] = round(time.time() - t0, 1)
    meta["rows_captured"] = len(rows)
    meta["rows_expected"] = total_expected
    meta["completed_marker_seen"] = done

    if rows:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header or
                       ["algorithm", "operation", "security_level",
                        "time_us", "run_number"])
            w.writerows(rows)

    # Per-operation reconciliation. A short capture is a dropped-row problem,
    # not something to paper over: report it per operation so it is obvious
    # which one to re-run.
    problems = []
    for key, exp in sorted(want.items()):
        got = seen.get(key, 0)
        if got != exp:
            problems.append((key, got, exp))
    meta["shortfalls"] = [
        {"algorithm": k[0], "operation": k[1], "security_level": k[2],
         "captured": g, "expected": e} for k, g, e in problems]

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"\nElapsed {meta['elapsed_s']/60:.1f} min, "
          f"{len(rows)}/{total_expected} rows.")
    print(f"  CSV:  {csv_path}")
    print(f"  log:  {log_path}")
    print(f"  meta: {meta_path}")

    if not done:
        print("\nWARNING: completion marker never arrived — capture is "
              "incomplete. Re-flash and re-run this firmware.")
    if problems:
        print("\nWARNING: row-count mismatch (dropped USB rows or early stop):")
        for (algo, op, lvl), got, exp in problems:
            print(f"  {algo:12s} {op:14s} {lvl:>5s}: {got}/{exp}")
        print("Re-run this firmware before using the data.")
        return 1
    if not done:
        return 1

    print("\nAll expected rows captured.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
