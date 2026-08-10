#!/usr/bin/env python3
"""Sensitivity of the iteration-recovery fit to the t_min anchor.

The affine timing model t = t_min + (k-1)*c + b*f anchors t_min at the single
fastest observed signature. That is an extreme order statistic of a noisy
process, so timing noise on one sample propagates into every recovered
iteration count and into the setup/marginal-cost split. This script quantifies
that exposure three ways:

  1. re-anchor on the 2nd, 3rd, 5th, 10th, 25th and 100th fastest samples;
  2. refit with t_min as a free parameter jointly with (c, f);
  3. bootstrap the anchor to get an interval on t_min itself.

Reference: Section V-E of the paper. Run from the repository root.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_campaign_b import recover_iterations  # noqa: E402

CSV_B = "results/campaign_b/rp2040_campaign_b.csv"
OUT = "results/campaign_b/tmin_sensitivity.json"

# Published fit (Section V-E), used as the comparison point.
PAPER_C = 28.91
PAPER_F = 5.91
PAPER_EK = 4.34


def load_sign():
    d = pd.read_csv(CSV_B)
    m = ((d.algorithm == "ML-DSA") & (d.operation == "sign")
         & (d.security_level == 44))
    return np.sort(d.loc[m, "time_us"].to_numpy(dtype=float) / 1000.0)


def rms_at(v, c, f, t_min):
    """Residual of the lattice fit at a given anchor, matching best_f()."""
    d = v - t_min
    a = np.floor(d / c)
    rem = d - a * c
    b = np.round(rem / f)
    r = np.where(b * f >= c, d - (a + 1) * c, rem - b * f)
    return float(np.sqrt(np.mean(r ** 2)))


def refit_cf(v, t_min, c0=PAPER_C, f0=PAPER_F, pad=0.10, step=0.01):
    """Re-optimise (c, f) near the published values at a fixed anchor."""
    d = v - t_min
    best = (np.inf, None, None)
    for c in np.arange(c0 * (1 - pad), c0 * (1 + pad), step):
        a = np.floor(d / c)
        rem = d - a * c
        for f in np.arange(f0 * (1 - pad), f0 * (1 + pad), step):
            b = np.round(rem / f)
            r = np.where(b * f >= c, d - (a + 1) * c, rem - b * f)
            rms = float(np.sqrt(np.mean(r ** 2)))
            if rms < best[0]:
                best = (rms, float(c), float(f))
    return best


def main():
    if not os.path.exists(CSV_B):
        sys.exit(f"missing {CSV_B}; run from the repository root")
    v = load_sign()
    n = len(v)
    t_min = float(v[0])

    print(f"ML-DSA-44 signing, campaign B: n={n}")
    print(f"published anchor t_min = {t_min:.3f} ms "
          f"(fastest of {n}), c={PAPER_C}, f={PAPER_F}\n")

    # --- 1. alternative order-statistic anchors -------------------------
    print(f"{'anchor':>10s} {'t_min(ms)':>10s} {'d vs min':>9s} "
          f"{'E[k]':>7s} {'dE[k]%':>8s} {'c':>7s} {'f':>6s} {'rms':>7s}")
    rows = []
    for rank in [1, 2, 3, 5, 10, 25, 100]:
        tm = float(v[rank - 1])
        rms, c, f = refit_cf(v, tm)
        ek = float(recover_iterations(v, c, f, tm).mean())
        rows.append(dict(anchor_rank=rank, t_min_ms=tm, c=c, f=f,
                         rms_ms=rms, ek=ek,
                         ek_pct_change=100.0 * (ek - PAPER_EK) / PAPER_EK))
        print(f"{rank:>10d} {tm:10.3f} {tm - t_min:+9.3f} {ek:7.3f} "
              f"{100.0 * (ek - PAPER_EK) / PAPER_EK:+8.2f} "
              f"{c:7.2f} {f:6.2f} {rms:7.4f}")

    eks = np.array([r["ek"] for r in rows])
    print(f"\nE[k] across anchors: {eks.min():.3f}-{eks.max():.3f} "
          f"(spread {100.0 * (eks.max() - eks.min()) / eks.mean():.2f}% of mean)")

    # --- 2. t_min as a free parameter -----------------------------------
    # Search below the fastest observation as well as above: the true fixed
    # cost can only be <= the fastest single-iteration signature, and is
    # strictly below it if even the fastest sample carried noise.
    best = (np.inf, None, None, None)
    for tm in np.arange(t_min - 3.0, t_min + 3.0, 0.01):
        rms, c, f = refit_cf(v, float(tm), pad=0.06, step=0.02)
        if rms < best[0]:
            best = (rms, float(tm), c, f)
    rms_free, tm_free, c_free, f_free = best
    ek_free = float(recover_iterations(v, c_free, f_free, tm_free).mean())
    print(f"\nfree-t_min refit: t_min={tm_free:.3f} ms "
          f"({tm_free - t_min:+.3f} vs anchored), c={c_free:.2f}, "
          f"f={f_free:.2f}, rms={rms_free:.4f}, E[k]={ek_free:.3f} "
          f"({100.0 * (ek_free - PAPER_EK) / PAPER_EK:+.2f}%)")

    # --- 3. bootstrap the anchor itself ---------------------------------
    rng = np.random.default_rng(20260810)
    bs = np.array([v[rng.integers(0, n, n)].min() for _ in range(2000)])
    lo, hi = np.percentile(bs, [2.5, 97.5])
    print(f"bootstrap 95% CI on the anchor: [{lo:.3f}, {hi:.3f}] ms "
          f"(width {hi - lo:.3f} ms = {100.0 * (hi - lo) / t_min:.3f}% of t_min)")

    setup_ms = 51.21
    print(f"\nsetup/marginal split: published {setup_ms:.2f} ms setup; "
          f"anchor uncertainty moves it by at most "
          f"{max(abs(hi - t_min), abs(t_min - lo)):.3f} ms "
          f"({100.0 * max(abs(hi - t_min), abs(t_min - lo)) / setup_ms:.2f}%)")

    out = dict(
        n=n, published=dict(c=PAPER_C, f=PAPER_F, ek=PAPER_EK,
                            t_min_ms=t_min, setup_ms=setup_ms),
        order_statistic_anchors=rows,
        ek_min=float(eks.min()), ek_max=float(eks.max()),
        ek_spread_pct=float(100.0 * (eks.max() - eks.min()) / eks.mean()),
        free_tmin=dict(t_min_ms=tm_free, c=c_free, f=f_free,
                       rms_ms=rms_free, ek=ek_free,
                       ek_pct_change=100.0 * (ek_free - PAPER_EK) / PAPER_EK),
        anchor_bootstrap_ci=[float(lo), float(hi)],
    )
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"\n  {OUT}")


if __name__ == "__main__":
    main()
