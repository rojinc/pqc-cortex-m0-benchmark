#!/usr/bin/env python3
"""Recompute every campaign-B number in the paper from the raw CSV and check it.

Reproduces the replication table, the signing-tail table, and the
rejection-sampling lattice fit reported in the paper's replication section.

Usage:  python scripts/verify_campaign_b.py
Exit status is non-zero if any published value fails to reproduce.
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSV_B = os.path.join(ROOT, "results", "campaign_b", "rp2040_campaign_b.csv")
RAW_A = os.path.join(ROOT, "results", "raw")

# Published values, transcribed from the paper.
PAPER_REPLICATION = {
    # operation:              (campaign A ms, campaign B ms, delta %, CV_B %)
    ("ML-KEM", "keygen", 512): (9.94, 11.31, 13.7, 0.52),
    ("ML-KEM", "encaps", 512): (11.53, 12.70, 10.1, 0.16),
    ("ML-KEM", "decaps", 512): (14.23, 14.84, 4.3, 0.12),
    ("ML-DSA", "keygen", 44): (39.83, 45.90, 15.2, 0.87),
    ("ML-DSA", "sign", 44): (158.91, 182.70, 15.0, 64.00),
    ("ML-DSA", "verify", 44): (43.98, 50.93, 15.8, 0.05),
}

PAPER_TAIL_B = {  # ML-DSA-44 signing, campaign B, milliseconds
    "mean": 182.70, "min": 80.12, "median": 143.91,
    "p95": 421.29, "p99": 584.20, "p99.9": 861.10, "max": 1156.79,
}

PAPER_FIT = {"c": 28.91, "f": 5.91, "t_min": 80.12,
             "mean_iters": 4.34, "max_iters": 38}

failures = []


def check(label, got, want, tol):
    ok = abs(got - want) <= tol
    print(f"  {'ok  ' if ok else 'FAIL'}  {label:<34} computed={got:10.3f}  paper={want:>9}")
    if not ok:
        failures.append(label)


def quantile_nearest(v, q):
    """Nearest-rank quantile: the smallest observation at or above rank q*n."""
    return np.sort(v)[int(np.ceil(q * len(v))) - 1]


def load_campaign_a():
    frames = []
    for name in os.listdir(RAW_A):
        if name.endswith(".csv"):
            frames.append(pd.read_csv(os.path.join(RAW_A, name), comment="#"))
    return pd.concat(frames, ignore_index=True)


def series(df, alg, op, lvl):
    m = (df.algorithm == alg) & (df.operation == op) & (df.security_level == lvl)
    return df[m].time_us.values / 1000.0


def recover_iterations(t, c, f, t_min):
    """Recover the rejection-sampling iteration count of each signature.

    Greedy assignment, matching the fit: take as many whole iteration steps c as
    fit, then round the remainder to the nearest multiple of the early-abort
    quantum f — carrying into the iteration count when that rounding reaches a
    full c. Iteration count is a+1 because the accepted attempt is also an
    iteration. Dropping the carry term biases the count low and inflates the
    apparent single-iteration fraction.
    """
    d = t - t_min
    a = np.floor(d / c)
    rem = d - a * c
    b = np.round(rem / f)
    a = np.where(b * f >= c, a + 1, a)
    return a + 1


def fit_lattice(t, c_range, f_range, step=0.01):
    """Grid-search the two-step lattice of the paper's iteration-recovery method.

    Model: t_i = t_min + a_i*c + b_i*f, with a_i, b_i non-negative integers
    assigned greedily. Loss is RMS residual; it is piecewise constant in the
    integers and therefore not differentiable, so a grid is used rather than a
    gradient method.
    """
    t_min = t.min()
    d = t - t_min
    best = (np.inf, None, None)
    for c in np.arange(*c_range, step):
        a = np.floor(d / c)
        rem = d - a * c
        for f in np.arange(*f_range, step):
            b = np.round(rem / f)
            resid = rem - b * f
            carry = b * f >= c
            r = np.where(carry, d - (a + 1) * c, resid)
            rms = float(np.sqrt(np.mean(r ** 2)))
            if rms < best[0]:
                best = (rms, c, f)
    return best[1], best[2], best[0], t_min


def main():
    if not os.path.exists(CSV_B):
        sys.exit(f"missing {CSV_B}")
    b = pd.read_csv(CSV_B, comment="#")
    a = load_campaign_a()

    print("\n[1] Replication table — campaign A vs campaign B")
    for (alg, op, lvl), (pa, pb, pdelta, pcv) in PAPER_REPLICATION.items():
        va, vb = series(a, alg, op, lvl), series(b, alg, op, lvl)
        check(f"{alg}-{lvl} {op} mean A", va.mean(), pa, 0.01)
        check(f"{alg}-{lvl} {op} mean B", vb.mean(), pb, 0.01)
        check(f"{alg}-{lvl} {op} delta %",
              100 * (vb.mean() - va.mean()) / va.mean(), pdelta, 0.06)
        check(f"{alg}-{lvl} {op} CV_B %",
              100 * vb.std(ddof=1) / vb.mean(), pcv, 0.01)

    print("\n[2] Signing tail — ML-DSA-44, campaign B (n=10,000)")
    v = series(b, "ML-DSA", "sign", 44)
    if len(v) != 10000:
        failures.append(f"expected 10000 signing rows, found {len(v)}")
    got = {"mean": v.mean(), "min": v.min(), "median": float(np.median(v)),
           "p95": quantile_nearest(v, .95), "p99": quantile_nearest(v, .99),
           "p99.9": quantile_nearest(v, .999), "max": v.max()}
    for k, want in PAPER_TAIL_B.items():
        check(f"signing {k}", got[k], want, 0.011)

    print("\n[3] Paper's qualitative tail claims")
    a_sign = series(a, "ML-DSA", "sign", 44)
    check("p99 understatement %", 100 * (got["p99"] - quantile_nearest(a_sign, .99))
          / got["p99"], 16, 0.5)
    check("max / min ratio", got["max"] / got["min"], 14.4, 0.05)
    check("max / median ratio", got["max"] / got["median"], 8.0, 0.05)

    print("\n[4] Rejection-sampling lattice fit (grid search)")
    c, f, rms, t_min = fit_lattice(v, (28.0, 30.0), (5.5, 7.5))
    check("iteration step c (ms)", c, PAPER_FIT["c"], 0.011)
    check("early-abort step f (ms)", f, PAPER_FIT["f"], 0.011)
    check("t_min (ms)", t_min, PAPER_FIT["t_min"], 0.011)
    print(f"        RMS residual = {rms:.3f} ms ({100 * rms / v.mean():.3f}% of mean)")

    iters = recover_iterations(v, c, f, t_min)
    check("mean recovered iterations", iters.mean(), PAPER_FIT["mean_iters"], 0.01)
    check("max recovered iterations", iters.max(), PAPER_FIT["max_iters"], 0)
    check("single-iteration fraction %", 100 * (iters == 1).mean(), 23.5, 0.05)
    # FIPS 204 predicts E[k] = 4.25 for ML-DSA-44; the fit is never told this.
    check("deviation from FIPS E[k]=4.25 (%)",
          100 * abs(iters.mean() - 4.25) / 4.25, 2.2, 0.15)

    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s) did not reproduce")
        for x in failures:
            print(f"  - {x}")
        return 1
    print("All campaign-B values in the paper reproduce from the raw data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
