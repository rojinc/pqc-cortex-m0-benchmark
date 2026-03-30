#!/usr/bin/env python3
"""Capture stack measurement lines from Pico serial output.

Saves all # STACK lines to a file. Auto-stops when it sees 'benchmarks complete'.

Usage:
    python scripts/capture_stack.py --port COM4 --output results/stack_data.txt
"""

import argparse
import sys
import serial


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True)
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    print(f"Opening {args.port} at {args.baud} baud...")
    print(f"Waiting for STACK lines (auto-stops on 'benchmarks complete')...\n")

    try:
        ser = serial.Serial(args.port, args.baud, timeout=1.0)
    except serial.SerialException as e:
        print(f"ERROR: Could not open {args.port}: {e}")
        sys.exit(1)

    stack_lines = []

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

            if "# STACK" in line:
                stack_lines.append(line)
                print(f"  >>> CAPTURED: {line}")

            if "benchmarks complete" in line:
                print("\nBenchmark complete, stopping.")
                break

    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        ser.close()

    if stack_lines:
        with open(args.output, "w") as f:
            for sl in stack_lines:
                f.write(sl + "\n")
        print(f"\nSaved {len(stack_lines)} stack measurements to {args.output}")
    else:
        print("\nNo stack data captured.")


if __name__ == "__main__":
    main()
