#!/usr/bin/env python3
"""
reproduce.py — Reproducibility toolkit for PQC-on-M0+ benchmarks.

Three modes:
  1. fingerprint  — Record build environment (compiler, SDK, PQClean commit, OS)
  2. collect      — Guided serial capture for all 3 benchmarks (flash → capture → save)
  3. compare      — Statistically compare two benchmark runs

Usage:
    python scripts/reproduce.py fingerprint
    python scripts/reproduce.py collect --port COM4 --run-id run2
    python scripts/reproduce.py compare --run1 results/raw --run2 results/raw_run2
"""

import argparse
import csv
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Fingerprint
# ---------------------------------------------------------------------------

def get_cmd_output(cmd):
    """Run a command and return stdout, or None on failure."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10,
            shell=isinstance(cmd, str)
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def fingerprint(args):
    """Record build environment to a JSON file."""
    print("Recording environment fingerprint...\n")

    info = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
        "compiler": {},
        "pqclean": {},
        "pico_sdk": {},
        "python": platform.python_version(),
    }

    # ARM GCC
    gcc_ver = get_cmd_output(["arm-none-eabi-gcc", "--version"])
    if gcc_ver:
        info["compiler"]["arm_none_eabi_gcc"] = gcc_ver.split("\n")[0]
    else:
        info["compiler"]["arm_none_eabi_gcc"] = "NOT FOUND"

    # PQClean commit
    pqclean_commit = get_cmd_output(["git", "-C", "pqclean", "rev-parse", "HEAD"])
    pqclean_describe = get_cmd_output(["git", "-C", "pqclean", "describe", "--tags"])
    info["pqclean"]["commit"] = pqclean_commit or "NOT FOUND"
    info["pqclean"]["tag"] = pqclean_describe or "N/A"

    # Pico SDK
    sdk_commit = get_cmd_output(["git", "-C", "pico-sdk", "rev-parse", "HEAD"])
    sdk_describe = get_cmd_output(["git", "-C", "pico-sdk", "describe", "--tags"])
    info["pico_sdk"]["commit"] = sdk_commit or "NOT FOUND"
    info["pico_sdk"]["tag"] = sdk_describe or "N/A"

    # Own repo
    own_commit = get_cmd_output(["git", "rev-parse", "HEAD"])
    own_dirty = get_cmd_output(["git", "status", "--porcelain"])
    info["repo"] = {
        "commit": own_commit or "NOT FOUND",
        "dirty": bool(own_dirty),
    }

    # Save
    out_path = args.output or "results/environment.json"
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(info, f, indent=2)

    print(f"  Platform:      {info['platform']['system']} {info['platform']['release']}")
    print(f"  Compiler:      {info['compiler']['arm_none_eabi_gcc']}")
    print(f"  PQClean:       {info['pqclean']['tag']} ({info['pqclean']['commit'][:10]}...)")
    print(f"  Pico SDK:      {info['pico_sdk']['tag']} ({info['pico_sdk']['commit'][:10]}...)")
    print(f"  Repo commit:   {info['repo']['commit'][:10]}... {'(dirty)' if info['repo']['dirty'] else '(clean)'}")
    print(f"  Python:        {info['python']}")
    print(f"\n  Saved to {out_path}")


# ---------------------------------------------------------------------------
# Collect — guided serial capture
# ---------------------------------------------------------------------------

BENCHMARKS = [
    {
        "name": "bench_mlkem",
        "output": "mlkem_pico.csv",
        "description": "ML-KEM (FIPS 203) — 512/768/1024",
        "est_minutes": 3,
    },
    {
        "name": "bench_mldsa",
        "output": "mldsa_pico.csv",
        "description": "ML-DSA (FIPS 204) — 44/65/87 (100 signing runs)",
        "est_minutes": 12,
    },
    {
        "name": "bench_classical",
        "output": "classical_pico.csv",
        "description": "RSA-2048, ECDSA/ECDH P-256 (RSA keygen is slow!)",
        "est_minutes": 20,
    },
]


def collect(args):
    """Guide user through flashing and capturing all 3 benchmarks."""
    try:
        import serial  # noqa: F401
    except ImportError:
        print("ERROR: pyserial not installed. Run: pip install pyserial")
        sys.exit(1)

    run_id = args.run_id or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_dir = os.path.join("results", run_id)
    os.makedirs(out_dir, exist_ok=True)

    print(f"{'='*60}")
    print(f"  PQC Benchmark Collection — {run_id}")
    print(f"  Output directory: {out_dir}")
    print(f"  Serial port: {args.port}")
    print(f"{'='*60}\n")

    # Save fingerprint alongside data
    fp_args = argparse.Namespace(output=os.path.join(out_dir, "environment.json"))
    fingerprint(fp_args)
    print()

    for i, bench in enumerate(BENCHMARKS, 1):
        uf2_path = os.path.join("build", f"{bench['name']}.uf2")
        out_csv = os.path.join(out_dir, bench["output"])

        print(f"\n{'='*60}")
        print(f"  Step {i}/3: {bench['description']}")
        print(f"  UF2: {uf2_path}")
        print(f"  Output: {out_csv}")
        print(f"  Estimated time: ~{bench['est_minutes']} minutes")
        print(f"{'='*60}")

        if not os.path.exists(uf2_path):
            print(f"  WARNING: {uf2_path} not found! Build firmware first.")
            print(f"  Skipping {bench['name']}...")
            continue

        print(f"\n  Instructions:")
        print(f"  1. Hold BOOTSEL on the Pico, plug in USB (or press BOOTSEL + reset)")
        print(f"  2. Copy {uf2_path} to the RPI-RP2 drive")
        print(f"  3. Wait for Pico to reboot (~2 seconds)")
        print(f"  4. Press Enter here to start capturing serial output")
        print(f"     (Press 's' + Enter to skip this benchmark)\n")

        choice = input("  > ").strip().lower()
        if choice == "s":
            print(f"  Skipped {bench['name']}")
            continue

        print(f"\n  Capturing from {args.port}... (Ctrl+C when benchmark finishes)\n")

        # Capture serial data
        try:
            import serial as ser_mod
            port = ser_mod.Serial(args.port, 115200, timeout=1.0)
            time.sleep(2)  # CDC settle time (Windows workaround)

            csv_rows = []
            header_written = False
            data_count = 0

            while True:
                raw = port.readline()
                if not raw:
                    continue
                try:
                    line = raw.decode("utf-8").strip()
                except UnicodeDecodeError:
                    continue
                if not line:
                    continue

                print(f"    {line}")

                if line.startswith("#"):
                    continue
                if line.startswith("algorithm,"):
                    if not header_written:
                        csv_rows.append(line.split(","))
                        header_written = True
                    continue

                parts = line.split(",")
                if len(parts) >= 5:
                    csv_rows.append(parts)
                    data_count += 1

        except KeyboardInterrupt:
            print(f"\n  Stopped. Collected {data_count} data points.")
        except Exception as e:
            print(f"  ERROR: {e}")
            continue
        finally:
            try:
                port.close()
            except Exception:
                pass

        if csv_rows:
            with open(out_csv, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerows(csv_rows)
            print(f"  Saved {data_count} rows to {out_csv}")
        else:
            print(f"  WARNING: No data collected for {bench['name']}")

    # Add energy column
    print(f"\n{'='*60}")
    print(f"  Post-processing: adding energy estimates...")
    print(f"{'='*60}")
    try:
        subprocess.run(
            [sys.executable, "scripts/add_energy.py", "--dir", out_dir],
            check=True
        )
    except subprocess.CalledProcessError:
        print("  WARNING: add_energy.py failed — run manually")

    # Validate
    print(f"\n{'='*60}")
    print(f"  Validating data quality...")
    print(f"{'='*60}")
    try:
        subprocess.run(
            [sys.executable, "scripts/validate_data.py", "--dir", out_dir],
            check=True
        )
    except subprocess.CalledProcessError:
        print("  WARNING: validation reported issues — check output above")

    print(f"\n{'='*60}")
    print(f"  Collection complete: {out_dir}/")
    print(f"  Next step: python scripts/reproduce.py compare --run1 results/raw --run2 {out_dir}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Compare — statistical comparison of two runs
# ---------------------------------------------------------------------------

def load_run(directory):
    """Load all CSVs from a directory into a single DataFrame."""
    try:
        import pandas as pd
    except ImportError:
        print("ERROR: pandas not installed. Run: pip install pandas")
        sys.exit(1)

    frames = []
    for f in sorted(os.listdir(directory)):
        if f.endswith(".csv"):
            df = pd.read_csv(os.path.join(directory, f))
            frames.append(df)
    if not frames:
        print(f"ERROR: No CSV files in {directory}")
        sys.exit(1)
    return pd.concat(frames, ignore_index=True)


def compare(args):
    """Statistically compare two benchmark runs."""
    import pandas as pd
    import numpy as np
    from scipy import stats as sp_stats

    print(f"\n{'='*70}")
    print(f"  Reproducibility Comparison")
    print(f"  Run 1 (reference): {args.run1}")
    print(f"  Run 2 (new):       {args.run2}")
    print(f"{'='*70}\n")

    df1 = load_run(args.run1)
    df2 = load_run(args.run2)

    # Tolerance thresholds
    MEAN_DIFF_WARN = 2.0    # % — flag if means differ by more than this
    MEAN_DIFF_FAIL = 5.0    # % — fail if means differ by more than this
    CV_DIFF_WARN = 10.0     # absolute percentage points for CV difference

    results = []
    total_pass = 0
    total_warn = 0
    total_fail = 0

    groups1 = df1.groupby(["algorithm", "operation", "security_level"])
    groups2 = df2.groupby(["algorithm", "operation", "security_level"])

    all_keys = sorted(set(groups1.groups.keys()) | set(groups2.groups.keys()))

    print(f"  {'Algorithm':<12} {'Operation':<15} {'Lvl':<5} "
          f"{'Mean1 (µs)':>12} {'Mean2 (µs)':>12} {'Diff%':>7} "
          f"{'CV1%':>6} {'CV2%':>6} {'t-stat':>8} {'p-val':>8} {'Result':>8}")
    print(f"  {'-'*105}")

    for key in all_keys:
        algo, op, level = key

        if key not in groups1.groups:
            print(f"  {algo:<12} {op:<15} {level:<5}  MISSING in run1")
            total_fail += 1
            results.append((*key, "MISSING_RUN1", None, None, None))
            continue
        if key not in groups2.groups:
            print(f"  {algo:<12} {op:<15} {level:<5}  MISSING in run2")
            total_fail += 1
            results.append((*key, "MISSING_RUN2", None, None, None))
            continue

        t1 = groups1.get_group(key)["time_us"]
        t2 = groups2.get_group(key)["time_us"]

        mean1, mean2 = t1.mean(), t2.mean()
        cv1 = (t1.std() / mean1 * 100) if mean1 > 0 else 0
        cv2 = (t2.std() / mean2 * 100) if mean2 > 0 else 0
        diff_pct = abs(mean2 - mean1) / mean1 * 100

        # Welch's t-test (unequal variance)
        t_stat, p_val = sp_stats.ttest_ind(t1, t2, equal_var=False)

        # Determine result
        is_variable = (algo == "ML-DSA" and op == "sign") or \
                      (algo == "RSA-2048" and op == "keygen")

        if is_variable:
            # For high-variance ops, use wider tolerance
            if diff_pct > MEAN_DIFF_FAIL * 3:
                verdict = "FAIL"
                total_fail += 1
            elif diff_pct > MEAN_DIFF_WARN * 3:
                verdict = "WARN"
                total_warn += 1
            else:
                verdict = "PASS"
                total_pass += 1
        else:
            if diff_pct > MEAN_DIFF_FAIL:
                verdict = "FAIL"
                total_fail += 1
            elif diff_pct > MEAN_DIFF_WARN:
                verdict = "WARN"
                total_warn += 1
            else:
                verdict = "PASS"
                total_pass += 1

        marker = {"PASS": "  ", "WARN": "! ", "FAIL": "X "}[verdict]

        print(f"{marker}{algo:<12} {op:<15} {level:<5} "
              f"{mean1:>12,.0f} {mean2:>12,.0f} {diff_pct:>6.2f}% "
              f"{cv1:>5.1f}% {cv2:>5.1f}% {t_stat:>8.2f} {p_val:>8.4f} {verdict:>8}")

        results.append((algo, op, level, verdict, diff_pct, p_val, {
            "mean1": mean1, "mean2": mean2,
            "cv1": cv1, "cv2": cv2,
            "n1": len(t1), "n2": len(t2),
            "t_stat": t_stat, "p_val": p_val,
        }))

    # Summary
    total = total_pass + total_warn + total_fail
    print(f"\n{'='*70}")
    print(f"  SUMMARY: {total_pass}/{total} PASS, {total_warn} WARN, {total_fail} FAIL")
    print(f"{'='*70}")
    print(f"\n  Thresholds:")
    print(f"    Deterministic ops: WARN >{MEAN_DIFF_WARN}%, FAIL >{MEAN_DIFF_FAIL}%")
    print(f"    Variable ops (ML-DSA sign, RSA keygen): 3x wider tolerance")
    print(f"    Welch's t-test p-values shown for reference (p<0.05 = significant difference)")

    # Save report
    report_path = args.report or "results/reproducibility_report.json"
    os.makedirs(os.path.dirname(report_path) or ".", exist_ok=True)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run1": os.path.abspath(args.run1),
        "run2": os.path.abspath(args.run2),
        "summary": {
            "total": total,
            "pass": total_pass,
            "warn": total_warn,
            "fail": total_fail,
            "reproducible": total_fail == 0,
        },
        "thresholds": {
            "mean_diff_warn_pct": MEAN_DIFF_WARN,
            "mean_diff_fail_pct": MEAN_DIFF_FAIL,
            "variable_ops_multiplier": 3,
        },
        "comparisons": [
            {
                "algorithm": r[0], "operation": r[1], "security_level": r[2],
                "verdict": r[3],
                "mean_diff_pct": round(r[4], 4) if r[4] is not None else None,
                "details": r[6] if len(r) > 6 else None,
            }
            for r in results
        ],
    }

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n  Report saved to {report_path}")

    if total_fail == 0:
        print(f"\n  RESULT: Data is REPRODUCIBLE within tolerance.")
        print(f"  Include this report in your submission as evidence.")
    else:
        print(f"\n  RESULT: {total_fail} comparison(s) FAILED — investigate before publishing.")

    return 0 if total_fail == 0 else 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PQC-on-M0+ reproducibility toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/reproduce.py fingerprint
  python scripts/reproduce.py collect --port COM4 --run-id run2
  python scripts/reproduce.py compare --run1 results/raw --run2 results/run2
        """
    )
    sub = parser.add_subparsers(dest="command")

    # fingerprint
    fp = sub.add_parser("fingerprint", help="Record build environment")
    fp.add_argument("--output", default=None, help="Output JSON path")

    # collect
    col = sub.add_parser("collect", help="Guided benchmark collection")
    col.add_argument("--port", required=True, help="Serial port (e.g. COM4)")
    col.add_argument("--run-id", default=None, help="Run identifier (default: timestamped)")

    # compare
    cmp = sub.add_parser("compare", help="Compare two benchmark runs")
    cmp.add_argument("--run1", required=True, help="Directory with first run CSVs")
    cmp.add_argument("--run2", required=True, help="Directory with second run CSVs")
    cmp.add_argument("--report", default=None, help="Output report JSON path")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "fingerprint":
        fingerprint(args)
    elif args.command == "collect":
        collect(args)
    elif args.command == "compare":
        sys.exit(compare(args))


if __name__ == "__main__":
    main()
