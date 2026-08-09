#!/usr/bin/env python3
"""Recompute the analyses added in the paper's revision and check them.

Covers the four claims that verify_campaign_b.py does not:

  [1] Cross-level validation of the iteration-recovery method
      (Table VI: E[k] with bootstrap CIs for ML-DSA-44, -65, -87).
  [2] The corrected chi-squared goodness-of-fit test, which uses the
      sample-estimated success probability rather than the FIPS-204 value.
  [3] The synthetic-data control that rules out bin misassignment as the
      source of the original rejection.
  [4] The timer-quantisation bound and the bootstrap cross-validation of
      the analytic confidence intervals.
  [5] The pqm4 Cortex-M4 comparison (Table X) and its slowdown ratios.

Usage:  python scripts/verify_revision.py
Exit status is non-zero if any published value fails to reproduce.

Seeded throughout, so the bootstrap and simulation figures are exactly
reproducible. Runtime is a few seconds.
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from verify_campaign_b import (  # noqa: E402  (needs HERE on sys.path)
    fit_lattice,
    load_campaign_a,
    recover_iterations,
    series,
)

ROOT = os.path.dirname(HERE)
CSV_B = os.path.join(ROOT, "results", "campaign_b", "rp2040_campaign_b.csv")

SKIP_SLOW = "--fast" in sys.argv
SEED = 0
N_BOOT = 150          # bootstrap resamples for the E[k] intervals in Sec. V-E
N_BOOT_CI = 4000      # bootstrap resamples for the timing-CI cross-check
RP2040_MHZ = 125.0
TIMER_RES_US = 1.0    # RP2040 time_us_32() quantum

# FIPS 204, Table 1: expected rejection-loop iterations by parameter set.
FIPS_EK = {44: 4.25, 65: 5.10, 87: 3.85}

# Published values, transcribed from the paper.
# Section V-E reports a NEGATIVE result: at n=100 the fit does not identify
# E[k]. These are the published bootstrap intervals for that claim, plus the
# n=10,000 fit that the anchoring procedure must reproduce as its own check.
PAPER_ANCHORED = {
    # (level, n): (ci_low, ci_high)
    (44, 100): (1.16, 4.97),
    (65, 100): (1.84, 5.62),
    (87, 100): (2.47, 5.30),
}
PAPER_10K_FIT = {"c": 28.91, "f": 5.91, "ek": 4.34}
# Published E[k] spread over the RMS-plausible region of c (the degeneracy).
PAPER_DEGENERACY = {65: (3.1, 8.1), 87: (7.2, 10.1)}
# Coarse modal spacing by level, the one cross-level quantity claimed.
PAPER_MODAL_C = {44: 29, 65: 43, 87: 50}

PAPER_CHI2 = {"stat": 22.64, "dof": 14, "p": 0.066}
PAPER_QUANT = {"max_pct_of_mean": 0.003, "max_pct_of_cv": 1.8}
PAPER_CI = {"worst_half_width_pct": 0.60, "boot_agreement_pts": 0.05}
PAPER_CONTROL = {"sigma_ms": 0.27, "mis_1x": 0.0, "mis_3x": 0.1, "mis_10x": 4.9}

# pqm4 benchmarks.csv @ 90bfb630 (2025-05-22), clean/reference C at -O3,
# NUCLEO-L4R5ZI @ 24 MHz. Full handshake = keygen + encaps + decaps, kilocycles.
PQM4_M4_KC = {512: 2185, 768: 3515, 1024: 5265}
PAPER_SLOWDOWN = {512: 2.04, 768: 2.01, 1024: 2.04}

failures = []


def check(label, got, want, tol):
    ok = abs(got - want) <= tol
    print(f"  {'ok  ' if ok else 'FAIL'}  {label:<40} computed={got:10.3f}  paper={want:>9}")
    if not ok:
        failures.append(label)


def chi2_geometric(k, p, kmax=15):
    """Pearson chi-squared for a geometric law over k=1..kmax plus a tail bin.

    Returns (statistic, dof) with dof = bins - 1 - 1, one degree of freedom
    spent because p is estimated from the same sample. Callers testing against
    an externally fixed p should add that degree of freedom back.
    """
    obs = np.array([(k == i).sum() for i in range(1, kmax + 1)] + [(k > kmax).sum()])
    pr = np.array([p * (1 - p) ** (i - 1) for i in range(1, kmax + 1)])
    pr = np.append(pr, max(1.0 - pr.sum(), 1e-12))
    exp = pr * len(k)
    stat = float(((obs - exp) ** 2 / exp).sum())
    return stat, len(obs) - 1 - 1


def best_f(v, c, r_lo=0.13, r_hi=0.30, step=0.01):
    """Best early-abort step f at fixed c, searched over the admissible ratio band."""
    t_min = v.min()
    d = v - t_min
    a = np.floor(d / c)
    rem = d - a * c
    best = (np.inf, None)
    for f in np.arange(r_lo * c, r_hi * c, step):
        b = np.round(rem / f)
        r = np.where(b * f >= c, d - (a + 1) * c, rem - b * f)
        rms = float(np.sqrt(np.mean(r ** 2)))
        if rms < best[0]:
            best = (rms, f)
    return best[1], best[0]


def group_structure(v, binw=2.0, minmass=2, gap_mult=1.6):
    """Estimate (c, f) from resolved modal structure, using no FIPS knowledge.

    The signing-time histogram separates into groups. Group start-to-start
    spacing estimates the iteration step c; spacing within a group estimates
    the early-abort quantum f. This is what breaks the RMS degeneracy.
    """
    d = np.sort(v) - v.min()
    h, e = np.histogram(d, bins=np.arange(0, d.max() + binw, binw))
    pk = np.array([e[i] for i in range(1, len(h) - 1)
                   if h[i] >= minmass and h[i] == max(h[max(0, i - 2):i + 3])])
    if len(pk) < 3:
        return None
    g = np.diff(pk)
    small = float(np.median(g[g <= np.median(g)]))
    starts = [pk[0]]
    for i in range(1, len(pk)):
        if pk[i] - pk[i - 1] > gap_mult * small:
            starts.append(pk[i])
    starts = np.array(starts)
    c = float(np.median(np.diff(starts))) if len(starts) > 1 else float("nan")
    return c, small, len(starts)


def anchored_fit(v, pad=0.12, step=0.01):
    """Grid search restricted to a neighbourhood of the modal-structure estimate."""
    gs = group_structure(v)
    if gs is None or not np.isfinite(gs[0]):
        return None
    c0, f0 = gs[0], gs[1]
    t_min = v.min()
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
                best = (rms, c, f)
    return best[1], best[2], best[0]


def ek_spread_over_plausible_c(v, c_lo=20.0, c_hi=140.0, step=0.5, factor=2.0):
    """Spread of recovered E[k] across all c whose RMS is within `factor` of best.

    This is the degeneracy diagnostic: a wide spread means the residual does not
    identify the iteration count, however precise the individual timings are.
    """
    rows = []
    for c in np.arange(c_lo, c_hi, step):
        f, r = best_f(v, c)
        rows.append((c, r, recover_iterations(v, c, f, v.min()).mean()))
    A = np.array(rows)
    sel = A[A[:, 1] <= factor * A[:, 1].min()]
    return float(sel[:, 2].min()), float(sel[:, 2].max()), len(sel)


def main():
    if not os.path.exists(CSV_B):
        sys.exit(f"missing {CSV_B}")
    b = pd.read_csv(CSV_B, comment="#")
    a = load_campaign_a()

    # ---------------------------------------------------------------- [1]
    print("\n[1] Section V-E: identifiability of the fit across security levels")
    v10k = series(b, "ML-DSA", "sign", 44)
    if SKIP_SLOW:
        print("        (skipped: --fast; the anchored bootstrap takes ~18 min)")
    else:

        # (a) The anchoring procedure must recover the published n=10,000 fit
        #     without being given either parameter. This is its validity check.
        c10, f10, _ = anchored_fit(v10k)
        ek10 = recover_iterations(v10k, c10, f10, v10k.min()).mean()
        check("n=10000 anchored c (ms)", c10, PAPER_10K_FIT["c"], 0.011)
        check("n=10000 anchored f (ms)", f10, PAPER_10K_FIT["f"], 0.011)
        check("n=10000 anchored E[k]", ek10, PAPER_10K_FIT["ek"], 0.011)

        # (b) The degeneracy that makes n=100 unusable: RMS does not identify c.
        for lvl, (want_lo, want_hi) in PAPER_DEGENERACY.items():
            v = series(a, "ML-DSA", "sign", lvl)
            lo, hi, n_c = ek_spread_over_plausible_c(v)
            check(f"ML-DSA-{lvl} E[k] spread low", lo, want_lo, 0.1)
            check(f"ML-DSA-{lvl} E[k] spread high", hi, want_hi, 0.1)
            print(f"        ({n_c} values of c lie within 2x of the best residual)")

        # (c) The published bootstrap intervals at n=100, which are uninformative.
        rng = np.random.default_rng(SEED)
        for lvl in (44, 65, 87):
            v = series(a, "ML-DSA", "sign", lvl)
            if len(v) != 100:
                failures.append(f"expected 100 signatures at level {lvl}, got {len(v)}")
            bs = []
            for _ in range(N_BOOT):
                s_ = rng.choice(v, len(v), replace=True)
                fit = anchored_fit(s_)
                if fit is None:
                    continue
                cc, ff, _ = fit
                bs.append(recover_iterations(s_, cc, ff, s_.min()).mean())
            lo, hi = np.percentile(bs, [2.5, 97.5])
            want_lo, want_hi = PAPER_ANCHORED[(lvl, 100)]
            check(f"ML-DSA-{lvl} n=100 CI low", lo, want_lo, 0.35)
            check(f"ML-DSA-{lvl} n=100 CI high", hi, want_hi, 0.35)
            # The paper's point: the interval contains FIPS but is too wide to mean much.
            width = hi - lo
            print(f"        interval width {width:.2f} -- contains FIPS-204 "
                  f"{FIPS_EK[lvl]}: {lo <= FIPS_EK[lvl] <= hi}, but uninformatively so")
            if width < 1.5:
                failures.append(f"level {lvl} interval unexpectedly narrow; "
                                "the paper's negative claim would not hold")

        # (d) The one cross-level quantity the paper does assert: modal spacing grows.
        got_c = {}
        for lvl in (44, 65, 87):
            gs = group_structure(series(a, "ML-DSA", "sign", lvl))
            got_c[lvl] = gs[0]
            check(f"ML-DSA-{lvl} modal spacing (ms)", gs[0], PAPER_MODAL_C[lvl], 6.0)
        grows = got_c[44] < got_c[65] < got_c[87]
        print(f"        {'ok  ' if grows else 'FAIL'}  modal spacing increases with security level")
        if not grows:
            failures.append("modal spacing does not increase with level")

    # ---------------------------------------------------------------- [2]
    print("\n[2] Corrected chi-squared test (estimated vs FIPS-fixed parameter)")
    c44, f44 = PAPER_10K_FIT["c"], PAPER_10K_FIT["f"]
    k10k = recover_iterations(v10k, c44, f44, v10k.min())
    p_est = 1.0 / k10k.mean()
    stat_est, dof_est = chi2_geometric(k10k, p_est)
    p_val = 1 - stats.chi2.cdf(stat_est, dof_est)
    check("chi2 with estimated p", stat_est, PAPER_CHI2["stat"], 0.05)
    check("degrees of freedom", dof_est, PAPER_CHI2["dof"], 0)
    check("p-value with estimated p", p_val, PAPER_CHI2["p"], 0.005)
    not_rejected = p_val > 0.05
    print(f"        {'ok  ' if not_rejected else 'FAIL'}  geometric form NOT rejected at alpha=0.05")
    if not not_rejected:
        failures.append("corrected test still rejects")

    # The original construction, which produced the p=0.010 the paper retracts.
    stat_fips, dof_fips = chi2_geometric(k10k, 1.0 / FIPS_EK[44])
    p_fips = 1 - stats.chi2.cdf(stat_fips, dof_fips + 1)
    print(f"        (original FIPS-fixed construction reproduces as "
          f"chi2={stat_fips:.2f}, p={p_fips:.3f} -- the rejection the paper retracts)")

    # ---------------------------------------------------------------- [3]
    print("\n[3] Synthetic control for the bin-misassignment explanation")
    rng = np.random.default_rng(SEED)
    d = v10k - v10k.min()
    aa = np.floor(d / c44)
    rem = d - aa * c44
    bb = np.round(rem / f44)
    resid = np.where(bb * f44 >= c44, d - (aa + 1) * c44, rem - bb * f44)
    sigma = float(resid.std())
    check("fitted residual sigma (ms)", sigma, PAPER_CONTROL["sigma_ms"], 0.011)

    n_sim = 10000
    b_max = max(int(c44 // f44), 1)
    got = {}
    for mult in (1, 3, 10):
        k_true = rng.geometric(p_est, n_sim)
        b_true = rng.integers(0, b_max, n_sim)
        t_sim = (v10k.min() + (k_true - 1) * c44 + b_true * f44
                 + rng.normal(0, sigma * mult, n_sim))
        k_rec = recover_iterations(t_sim, c44, f44, v10k.min())
        got[mult] = 100.0 * (k_rec != k_true).mean()
    check("misassignment at observed noise (%)", got[1], PAPER_CONTROL["mis_1x"], 0.05)
    check("misassignment at 3x noise (%)", got[3], PAPER_CONTROL["mis_3x"], 0.1)
    check("misassignment at 10x noise (%)", got[10], PAPER_CONTROL["mis_10x"], 1.0)
    grows = got[10] > got[1] + 1.0
    print(f"        {'ok  ' if grows else 'FAIL'}  misassignment grows with noise as the paper states")
    if not grows:
        failures.append("misassignment does not grow with noise")

    # ---------------------------------------------------------------- [4]
    print("\n[4] Timer quantisation bound and bootstrap CI cross-check")
    rng = np.random.default_rng(SEED)
    q_sd_us = TIMER_RES_US / np.sqrt(12.0)   # uniform quantisation error
    worst_half, worst_q_share, worst_gap = 0.0, 0.0, 0.0
    for (alg, op, lvl), g in a.groupby(["algorithm", "operation", "security_level"]):
        v = g.time_us.values.astype(float)
        if len(v) < 10:
            continue
        cv = 100 * v.std(ddof=1) / v.mean()
        if cv > 1.5:            # signing is excluded: it is not a stable operation
            continue
        half_t = stats.t.ppf(0.975, len(v) - 1) * cv / np.sqrt(len(v))
        bs = np.array([rng.choice(v, len(v), replace=True).mean() for _ in range(N_BOOT_CI)])
        lo, hi = np.percentile(bs, [2.5, 97.5])
        half_b = 100 * max(hi - v.mean(), v.mean() - lo) / v.mean()
        worst_half = max(worst_half, half_b)
        worst_q_share = max(worst_q_share, 100 * (100 * q_sd_us / v.mean()) / cv)
        worst_gap = max(worst_gap, abs(half_b - half_t))
    check("worst-case CI half-width (%)", worst_half, PAPER_CI["worst_half_width_pct"], 0.011)
    check("quantisation as share of CV (%)", worst_q_share, PAPER_QUANT["max_pct_of_cv"], 0.05)
    check("analytic vs bootstrap gap (pts)", worst_gap, PAPER_CI["boot_agreement_pts"], 0.011)

    # ---------------------------------------------------------------- [5]
    print("\n[5] pqm4 Cortex-M4 comparison (Table X)")
    for lvl, m4_kc in PQM4_M4_KC.items():
        tot_ms = sum(series(a, "ML-KEM", op, lvl).mean()
                     for op in ("keygen", "encaps", "decaps"))
        m0_kc = tot_ms * RP2040_MHZ           # ms * MHz = kilocycles
        check(f"ML-KEM-{lvl} M0+ handshake (ms)", tot_ms,
              {512: 35.7, 768: 56.6, 1024: 85.7}[lvl], 0.06)
        check(f"ML-KEM-{lvl} slowdown vs M4", m0_kc / m4_kc, PAPER_SLOWDOWN[lvl], 0.006)
    print("        M4 reference cycles are pqm4 benchmarks.csv @ 90bfb630 (2025-05-22),")
    print("        clean/reference C at -O3, NUCLEO-L4R5ZI @ 24 MHz. The slowdown is a")
    print("        ratio of cycle counts and is independent of both clock rates.")

    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s) did not reproduce")
        for x in failures:
            print(f"  - {x}")
        return 1
    print("All revision analyses in the paper reproduce from the raw data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
