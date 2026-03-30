#!/usr/bin/env python3
"""
add_energy.py — Add energy_uj column to all benchmark CSV files.

Energy is estimated from the RP2040 datasheet:
  - Active current: ~24 mA at 3.3V, 133 MHz (single core executing)
  - Active power: 0.024 A × 3.3 V = 0.0792 W = 79.2 mW
  - Energy (µJ) = Power (W) × Time (µs) = 0.0792 × time_us

Source: RP2040 Datasheet, Section 5.4, Table 628 (typical values).
Note: This is a datasheet estimate, not per-operation oscilloscope measurement.
The methodology section of the paper must state this clearly.

Usage:
    python scripts/add_energy.py                    # Process all CSVs in results/raw/
    python scripts/add_energy.py --dir results/raw  # Explicit directory
    python scripts/add_energy.py --dry-run           # Preview without writing
"""

import argparse
import glob
import os
import sys
import pandas as pd

# RP2040 power model (datasheet estimate)
# RP2040 Datasheet, Section 5.4 — Typical current at DVDD + VREG_VIN
# Active (133 MHz, single core): ~24 mA at 3.3V supply
VOLTAGE_V = 3.3
ACTIVE_CURRENT_A = 0.024
ACTIVE_POWER_W = VOLTAGE_V * ACTIVE_CURRENT_A  # 0.0792 W


def add_energy_column(filepath, dry_run=False):
    """Add energy_uj column to a CSV file based on time_us."""
    fname = os.path.basename(filepath)

    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        print(f"  ERROR: Cannot read {fname}: {e}")
        return False

    if "time_us" not in df.columns:
        print(f"  SKIP: {fname} — no time_us column")
        return False

    # Calculate energy: E(µJ) = P(W) × t(µs)
    df["energy_uj"] = (df["time_us"] * ACTIVE_POWER_W).round(1)

    # Print summary
    print(f"\n  {fname}:")
    print(f"  {'Algorithm':<15} {'Operation':<15} {'Level':<6} "
          f"{'Mean Time (µs)':>15} {'Mean Energy (µJ)':>18} {'Energy (mJ)':>12}")
    print(f"  {'-'*85}")

    for (algo, op, level), group in df.groupby(
        ["algorithm", "operation", "security_level"]
    ):
        mean_time = group["time_us"].mean()
        mean_energy = group["energy_uj"].mean()
        energy_mj = mean_energy / 1000
        print(f"  {algo:<15} {op:<15} {level:<6} "
              f"{mean_time:>15,.0f} {mean_energy:>18,.1f} {energy_mj:>12,.3f}")

    if not dry_run:
        df.to_csv(filepath, index=False)
        print(f"  -> Written with energy_uj column")
    else:
        print(f"  -> DRY RUN: no changes written")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Add energy_uj column to benchmark CSVs (RP2040 datasheet estimate)"
    )
    parser.add_argument(
        "--dir", default="results/raw",
        help="Directory containing CSV files (default: results/raw)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview energy values without modifying files"
    )
    args = parser.parse_args()

    csv_files = glob.glob(os.path.join(args.dir, "*.csv"))
    if not csv_files:
        print(f"No CSV files found in {args.dir}")
        sys.exit(1)

    print(f"RP2040 Energy Model:")
    print(f"  Voltage:       {VOLTAGE_V} V")
    print(f"  Active current: {ACTIVE_CURRENT_A * 1000:.0f} mA (datasheet typical)")
    print(f"  Active power:   {ACTIVE_POWER_W * 1000:.1f} mW")
    print(f"  Formula:        energy_uj = time_us × {ACTIVE_POWER_W}")
    print(f"\nProcessing {len(csv_files)} CSV file(s) in {args.dir}")

    for filepath in sorted(csv_files):
        add_energy_column(filepath, dry_run=args.dry_run)

    print(f"\nDone. {'(DRY RUN — no files modified)' if args.dry_run else 'All files updated.'}")


if __name__ == "__main__":
    main()
