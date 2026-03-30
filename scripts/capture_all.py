#!/usr/bin/env python3
"""Capture all benchmark output from Pico: CSV timing data, stack measurements, and full log.

Auto-stops when it sees 'benchmarks complete'.

Usage:
    python scripts/capture_all.py --port COM4 --name mldsa
    python scripts/capture_all.py --port COM4 --name mlkem
    python scripts/capture_all.py --port COM4 --name classical

Outputs:
    results/raw/<name>_pico.csv        — timing CSV data
    results/raw/<name>_pico_full.txt   — full serial log (including comments)
    results/stack_<name>.txt           — stack measurement lines only
"""

import argparse
import csv
import os
import sys
import serial


def main():
    parser = argparse.ArgumentParser(description="Capture Pico benchmark output")
    parser.add_argument("--port", required=True, help="Serial port (e.g., COM4)")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--name", required=True, help="Benchmark name: mldsa, mlkem, or classical")
    args = parser.parse_args()

    os.makedirs("results/raw", exist_ok=True)

    csv_path = f"results/raw/{args.name}_pico.csv"
    full_path = f"results/raw/{args.name}_pico_full.txt"
    stack_path = f"results/stack_{args.name}.txt"

    print(f"Opening {args.port} at {args.baud} baud...")
    print(f"Outputs: {csv_path}, {full_path}, {stack_path}")
    print(f"Waiting for data (auto-stops on 'benchmarks complete')...\n")

    try:
        ser = serial.Serial(args.port, args.baud, timeout=1.0)
    except serial.SerialException as e:
        print(f"ERROR: Could not open {args.port}: {e}")
        sys.exit(1)

    csv_rows = []
    full_lines = []
    stack_lines = []
    header_written = False
    data_count = 0

    try:
        while True:
            raw = ser.readline()
            if not raw:
                continue
            try:
                line = raw.decode("utf-8").strip()
            except UnicodeDecodeError:
                continue
            if not line:
                continue

            print(line)
            full_lines.append(line)

            # Capture stack lines
            if "# STACK" in line or "# WARNING" in line:
                stack_lines.append(line)
                print(f"  >>> STACK: {line}")

            # Auto-stop
            if "benchmarks complete" in line:
                print("\nBenchmark complete, stopping.")
                break

            # CSV header
            if line.startswith("algorithm,"):
                if not header_written:
                    csv_rows.append(line.split(","))
                    header_written = True
                continue

            # Skip comments
            if line.startswith("#"):
                continue

            # CSV data
            parts = line.split(",")
            if len(parts) >= 5:
                csv_rows.append(parts)
                data_count += 1

    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        ser.close()

    # Save CSV
    if csv_rows:
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(csv_rows)
        print(f"Saved {data_count} data points to {csv_path}")

    # Save full log
    if full_lines:
        with open(full_path, "w") as f:
            for l in full_lines:
                f.write(l + "\n")
        print(f"Saved full log ({len(full_lines)} lines) to {full_path}")

    # Save stack
    if stack_lines:
        with open(stack_path, "w") as f:
            for l in stack_lines:
                f.write(l + "\n")
        print(f"Saved {len(stack_lines)} stack measurements to {stack_path}")
    else:
        print("No stack data captured.")


if __name__ == "__main__":
    main()
