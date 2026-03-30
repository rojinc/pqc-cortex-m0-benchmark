#!/usr/bin/env python3
"""
parse_serial.py — Read benchmark output from Pico over USB serial and save as CSV.

Usage:
    python scripts/parse_serial.py --port COM3 --output results/raw/output.csv
    python scripts/parse_serial.py --port /dev/ttyACM0 --output results/raw/output.csv

The script reads lines from the serial port, filters CSV data lines
(skipping comment lines starting with '#'), and saves to a CSV file.
Press Ctrl+C to stop recording.
"""

import argparse
import csv
import sys
import time
import serial


def parse_args():
    parser = argparse.ArgumentParser(
        description="Read PQC benchmark output from Pico serial port"
    )
    parser.add_argument(
        "--port", required=True,
        help="Serial port (e.g., COM3 on Windows, /dev/ttyACM0 on Linux)"
    )
    parser.add_argument(
        "--baud", type=int, default=115200,
        help="Baud rate (default: 115200)"
    )
    parser.add_argument(
        "--output", required=True,
        help="Output CSV file path (e.g., results/raw/mlkem_pico.csv)"
    )
    parser.add_argument(
        "--timeout", type=float, default=1.0,
        help="Serial read timeout in seconds"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"Opening {args.port} at {args.baud} baud...")
    print(f"Output: {args.output}")
    print("Press Ctrl+C to stop recording.\n")

    try:
        ser = serial.Serial(args.port, args.baud, timeout=args.timeout)
    except serial.SerialException as e:
        print(f"ERROR: Could not open {args.port}: {e}")
        sys.exit(1)

    csv_rows = []
    header_written = False
    line_count = 0
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

            line_count += 1

            # Print all lines to console for monitoring
            print(line)

            # Comment/summary lines start with '#'
            if line.startswith("#"):
                continue

            # Parse CSV header
            if line.startswith("algorithm,"):
                header = line.split(",")
                if not header_written:
                    csv_rows.append(header)
                    header_written = True
                continue

            # Parse data lines
            parts = line.split(",")
            if len(parts) >= 5:
                csv_rows.append(parts)
                data_count += 1
                if data_count % 10 == 0:
                    print(f"  [{data_count} data points collected]")

    except KeyboardInterrupt:
        print(f"\n\nStopped. Read {line_count} lines, collected {data_count} data points.")

    finally:
        ser.close()

    if csv_rows:
        with open(args.output, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(csv_rows)
        print(f"Saved {data_count} data points to {args.output}")
    else:
        print("No data collected.")


if __name__ == "__main__":
    main()
