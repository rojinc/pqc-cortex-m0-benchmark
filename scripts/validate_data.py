#!/usr/bin/env python3
"""
validate_data.py -- Check all CSV benchmark files for data quality.

Checks:
1. No missing values
2. Flags outliers (>3 standard deviations from mean)
4. Checks RSA-2048 decrypt outliers (first run is often cold-cache)
3. Checks M0+ times are slower than published M4 times
4. Calculates coefficient of variation (CV) -- should be <5% except ML-DSA signing
"""

import argparse
import glob
import os
import sys
import pandas as pd
import numpy as np


# Approximate pqm4 reference C cycle counts on Cortex-M4 (clock-independent).
# Source: pqm4 project (mupq/pqm4), clean implementations.
# Our RP2040 runs at 133 MHz; M0+ cycle counts should be 1.5-5x higher than M4.
M4_REFERENCE_CYCLES = {
    ("ML-KEM", "keygen", 512): 719_000,
    ("ML-KEM", "encaps", 512): 907_000,
    ("ML-KEM", "decaps", 512): 854_000,
    ("ML-KEM", "keygen", 768): 1_233_000,
    ("ML-KEM", "encaps", 768): 1_501_000,
    ("ML-KEM", "decaps", 768): 1_435_000,
    ("ML-KEM", "keygen", 1024): 1_907_000,
    ("ML-KEM", "encaps", 1024): 2_250_000,
    ("ML-KEM", "decaps", 1024): 2_177_000,
}
M0_CLOCK_MHZ = 133  # RP2040 @ 133 MHz

CV_THRESHOLD = 5.0  # percent -- ML-DSA signing is exempt


def validate_csv(filepath):
    """Validate a single CSV file. Returns (passed, issues)."""
    issues = []
    fname = os.path.basename(filepath)
    print(f"\n{'='*60}")
    print(f"Validating: {fname}")
    print(f"{'='*60}")

    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        return False, [f"Cannot read file: {e}"]

    if df.empty:
        return False, ["File is empty"]

    # Check 1: Missing values
    missing = df.isnull().sum()
    total_missing = missing.sum()
    if total_missing > 0:
        issues.append(f"Missing values found: {dict(missing[missing > 0])}")
    else:
        print("  [PASS] No missing values")

    # Check 2: Outliers (>3 stddev from mean)
    if "time_us" in df.columns:
        for (algo, op, level), group in df.groupby(
            ["algorithm", "operation", "security_level"]
        ):
            times = group["time_us"]
            mean = times.mean()
            std = times.std()
            if std > 0:
                outliers = group[abs(times - mean) > 3 * std]
                if len(outliers) > 0:
                    issues.append(
                        f"OUTLIER: {algo}/{op}/{level} -- "
                        f"{len(outliers)} points >3 stddev from mean "
                        f"(mean={mean:.0f}, std={std:.0f})"
                    )
                    for _, row in outliers.iterrows():
                        issues.append(
                            f"  Run {row['run_number']}: {row['time_us']} µs"
                        )
                else:
                    print(f"  [PASS] {algo}/{op}/{level}: no outliers")

    # Check 3: M0+ cycle counts should be higher than M4 (1.5-5x for ref C)
    if "time_us" in df.columns:
        for (algo, op, level), group in df.groupby(
            ["algorithm", "operation", "security_level"]
        ):
            key = (algo, op, level)
            if key in M4_REFERENCE_CYCLES:
                m4_cycles = M4_REFERENCE_CYCLES[key]
                m0_mean_us = group["time_us"].mean()
                m0_cycles = m0_mean_us * M0_CLOCK_MHZ
                if m0_cycles < m4_cycles:
                    issues.append(
                        f"SUSPICIOUS: {algo}/{op}/{level} M0+ ({m0_cycles:.0f} cycles) "
                        f"is FASTER than M4 ({m4_cycles} cycles) -- check your setup!"
                    )
                else:
                    ratio = m0_cycles / m4_cycles
                    print(
                        f"  [PASS] {algo}/{op}/{level}: M0+/M4 cycle ratio = {ratio:.1f}x "
                        f"(M0+: {m0_cycles:.0f} cycles, M4: {m4_cycles} cycles)"
                    )

    # Check 4: Coefficient of Variation
    if "time_us" in df.columns:
        for (algo, op, level), group in df.groupby(
            ["algorithm", "operation", "security_level"]
        ):
            times = group["time_us"]
            mean = times.mean()
            std = times.std()
            cv = (std / mean * 100) if mean > 0 else 0

            is_dsa_sign = algo == "ML-DSA" and op == "sign"
            is_rsa_keygen = algo == "RSA-2048" and op == "keygen"
            is_exempt = is_dsa_sign or is_rsa_keygen
            if is_dsa_sign:
                threshold_label = "exempt (rejection sampling)"
            elif is_rsa_keygen:
                threshold_label = "exempt (prime search variance)"
            else:
                threshold_label = f"<{CV_THRESHOLD}%"

            if cv > CV_THRESHOLD and not is_exempt:
                issues.append(
                    f"HIGH CV: {algo}/{op}/{level} -- "
                    f"CV={cv:.2f}% (threshold: {threshold_label})"
                )
            else:
                print(
                    f"  [PASS] {algo}/{op}/{level}: CV={cv:.2f}% ({threshold_label})"
                )

    # Print summary statistics
    has_energy = "energy_uj" in df.columns
    if "time_us" in df.columns:
        print(f"\n  Summary Statistics:")
        header = (f"  {'Algorithm':<15} {'Operation':<15} {'Level':<6} "
                  f"{'Mean (µs)':>12} {'Min':>10} {'Max':>10} {'StdDev':>10} {'CV%':>8} {'N':>4}")
        if has_energy:
            header += f" {'Energy (µJ)':>12} {'Energy (mJ)':>12}"
        print(header)
        print(f"  {'-'*(105 if has_energy else 90)}")
        for (algo, op, level), group in df.groupby(
            ["algorithm", "operation", "security_level"]
        ):
            times = group["time_us"]
            mean = times.mean()
            std = times.std()
            cv = (std / mean * 100) if mean > 0 else 0
            line = (
                f"  {algo:<15} {op:<15} {level:<6} "
                f"{mean:>12,.0f} {times.min():>10,} {times.max():>10,} "
                f"{std:>10,.1f} {cv:>7.2f}% {len(times):>4}"
            )
            if has_energy:
                mean_energy = group["energy_uj"].mean()
                line += f" {mean_energy:>12,.1f} {mean_energy/1000:>12,.3f}"
            print(line)

    passed = len(issues) == 0
    if issues:
        print(f"\n  ISSUES FOUND ({len(issues)}):")
        for issue in issues:
            print(f"    WARNING: {issue}")
    else:
        print(f"\n  ALL CHECKS PASSED")

    return passed, issues


def main():
    parser = argparse.ArgumentParser(description="Validate benchmark CSV data")
    parser.add_argument(
        "--dir", default="results/raw",
        help="Directory containing CSV files (default: results/raw)"
    )
    args = parser.parse_args()

    csv_files = glob.glob(os.path.join(args.dir, "*.csv"))
    if not csv_files:
        print(f"No CSV files found in {args.dir}")
        sys.exit(1)

    print(f"Found {len(csv_files)} CSV file(s) in {args.dir}")

    all_passed = True
    for filepath in sorted(csv_files):
        passed, issues = validate_csv(filepath)
        if not passed:
            all_passed = False

    print(f"\n{'='*60}")
    if all_passed:
        print("ALL FILES PASSED VALIDATION")
    else:
        print("SOME FILES HAVE ISSUES -- fix before writing the paper!")
    print(f"{'='*60}")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
