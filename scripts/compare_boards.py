#!/usr/bin/env python3
"""
compare_boards.py — Inter-unit agreement analysis for Campaign C.

Answers the reviewer's question: do two physical RP2040 units produce the
same timings, or is the paper's crystal-referenced-PLL argument wishful?

Method
------
For every operation we report the relative difference between board means
and a 95% confidence interval on that difference (Welch, unequal variances
not assumed equal). But a plain significance test is the wrong instrument
here, for a reason worth stating: with n=1000 per board, a difference of
0.05% becomes "statistically significant" while being physically irrelevant.
Rejecting the null would then argue AGAINST the paper for no good reason.

So the primary analysis is EQUIVALENCE, not difference. We use TOST (two
one-sided tests) against a margin of +/-1%: if the 90% CI for the relative
difference lies entirely within +/-1%, the two units are statistically
equivalent at that margin, and we can say so as a positive finding rather
than as a failure to reject.

The 1% margin is a judgement call and is declared here rather than tuned
after seeing the data: it is the level below which an inter-unit difference
could not change any engineering conclusion in the paper, since the paper's
own timer quantisation and optimisation-level effects are larger.

ML-DSA signing is reported but excluded from the equivalence claim. Its
variance is dominated by rejection sampling, not by silicon, so it cannot
resolve unit differences at any feasible sample size; the honest statement
is that it is uninformative here, and the deterministic operations carry
the result.

Usage
-----
    python scripts/compare_boards.py
    python scripts/compare_boards.py --margin 1.0 --outdir results/campaign_c
"""

import argparse
import glob
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

CAMPAIGN_C = os.path.join("results", "campaign_c")
RP2040_HZ = 125_000_000

# Minimum samples per board before a "different" verdict is permitted.
# Below this, an interval that excludes zero is not evidence of a board
# difference: the exact permutation test on n=3 vs n=3 has a floor of
# p=0.100, so significance is unreachable no matter how the data fall.
MIN_N_FOR_DIFFERENCE = 30


def parse_args():
    p = argparse.ArgumentParser(description="Campaign C inter-unit analysis")
    p.add_argument("--dir", default=CAMPAIGN_C,
                   help="Campaign C root (default results/campaign_c)")
    p.add_argument("--margin", type=float, default=1.0,
                   help="Equivalence margin in percent (default 1.0)")
    p.add_argument("--outdir", default=None,
                   help="Where to write outputs (default --dir)")
    return p.parse_args()


def load_board(root, board):
    """Load every firmware capture for one board into a single frame."""
    bdir = os.path.join(root, f"board{board}")
    if not os.path.isdir(bdir):
        sys.exit(f"Missing directory: {bdir}\n"
                 f"Run capture_campaign_c.py for board {board} first.")
    files = sorted(glob.glob(os.path.join(bdir, "*.csv")))
    if not files:
        sys.exit(f"No CSV captures in {bdir}")
    frames = []
    for f in files:
        d = pd.read_csv(f)
        d["source"] = os.path.basename(f)
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    df["board"] = board

    # Provenance: the board unique ID is what proves these are two different
    # physical units rather than one board captured twice. Without it the
    # whole comparison is unfalsifiable, so a missing ID is fatal.
    ids, clks = set(), set()
    for m in sorted(glob.glob(os.path.join(bdir, "*_meta.json"))):
        with open(m) as fh:
            meta = json.load(fh)
        if meta.get("board_unique_id"):
            ids.add(meta["board_unique_id"])
        if meta.get("clk_sys_hz"):
            clks.add(meta["clk_sys_hz"])
        if meta.get("shortfalls"):
            print(f"  WARNING: {os.path.basename(m)} recorded row shortfalls; "
                  f"data may be incomplete.")
    if not ids:
        sys.exit(f"No board unique ID found in {bdir}/*_meta.json — cannot "
                 f"verify board identity. Re-capture with the updated firmware.")
    if len(ids) > 1:
        sys.exit(f"Conflicting board IDs in {bdir}: {sorted(ids)} — captures "
                 f"from different boards were mixed into one directory.")
    return df, ids.pop(), (clks.pop() if len(clks) == 1 else None)


def welch(x, y):
    """Relative difference (percent of board 1) with Welch CI and TOST."""
    nx, ny = len(x), len(y)
    mx, my = x.mean(), y.mean()
    vx, vy = x.var(ddof=1), y.var(ddof=1)
    se = np.sqrt(vx / nx + vy / ny)
    if se == 0:
        # Both boards constant. Real case, not a degenerate one: randombytes()
        # at 32 and 64 bytes returned an identical value on all 2000 samples
        # per board, so both variances are exactly zero and Welch is undefined.
        # If the two constants agree the boards are identical on this
        # operation; if they differ, the difference is exact rather than
        # estimated. Either way the interval has zero width -- but every key
        # the caller reads must still be present.
        diff_pct = 0.0 if mx == my else 100.0 * (my - mx) / mx
        return dict(diff_pct=diff_pct, ci_lo=diff_pct, ci_hi=diff_pct,
                    tost_lo=diff_pct, tost_hi=diff_pct,
                    p=(1.0 if mx == my else 0.0), dof=np.nan)
    dof = (vx / nx + vy / ny) ** 2 / (
        (vx / nx) ** 2 / (nx - 1) + (vy / ny) ** 2 / (ny - 1))
    diff = my - mx
    tcrit95 = stats.t.ppf(0.975, dof)
    tcrit90 = stats.t.ppf(0.95, dof)     # 90% CI is the TOST-consistent one
    p = 2 * stats.t.sf(abs(diff / se), dof)
    return dict(
        diff_pct=100.0 * diff / mx,
        ci_lo=100.0 * (diff - tcrit95 * se) / mx,
        ci_hi=100.0 * (diff + tcrit95 * se) / mx,
        tost_lo=100.0 * (diff - tcrit90 * se) / mx,
        tost_hi=100.0 * (diff + tcrit90 * se) / mx,
        p=p, dof=dof,
    )


def main():
    args = parse_args()
    outdir = args.outdir or args.dir
    os.makedirs(outdir, exist_ok=True)

    print("Campaign C — inter-unit agreement\n")
    d1, id1, clk1 = load_board(args.dir, 1)
    d2, id2, clk2 = load_board(args.dir, 2)

    if id1 == id2:
        sys.exit(f"\nFATAL: both directories report the same board unique ID "
                 f"({id1}).\nThese are captures from ONE physical board — "
                 f"there is no inter-unit comparison to make.")

    print(f"  board 1: unique ID {id1}"
          + (f", clk_sys {clk1:,} Hz" if clk1 else ""))
    print(f"  board 2: unique ID {id2}"
          + (f", clk_sys {clk2:,} Hz" if clk2 else ""))
    if clk1 and clk2 and clk1 != clk2:
        print(f"  NOTE: boards report different clk_sys — timing differences "
              f"will partly reflect clock, not silicon.")
    print()

    keys = ["algorithm", "operation", "security_level"]
    common = (set(map(tuple, d1[keys].drop_duplicates().values))
              & set(map(tuple, d2[keys].drop_duplicates().values)))
    if not common:
        sys.exit("No operations present in both boards' captures.")

    rows = []
    for k in sorted(common):
        m1 = (d1[keys] == pd.Series(k, index=keys)).all(axis=1)
        m2 = (d2[keys] == pd.Series(k, index=keys)).all(axis=1)
        x = d1.loc[m1, "time_us"].to_numpy(float)
        y = d2.loc[m2, "time_us"].to_numpy(float)
        if len(x) < 2 or len(y) < 2:
            continue
        r = welch(x, y)
        cv1 = 100 * x.std(ddof=1) / x.mean()
        cv2 = 100 * y.std(ddof=1) / y.mean()
        # ML-DSA signing is rejection-sampling dominated: reported, but it
        # cannot resolve silicon differences and is excluded from the claim.
        informative = not (k[0] == "ML-DSA" and k[1] == "sign")

        # Three outcomes, not two. Collapsing them into equivalent/not
        # would misreport low-power operations: RSA-2048 keygen runs at
        # n=3 (each sample takes minutes), so its interval spans hundreds
        # of percent. That is an absence of evidence, not evidence of a
        # difference, and calling it "not equivalent" would hand a reviewer
        # a false alarm.
        #
        #   equivalent   — CI inside the margin: units agree
        #   different    — CI excludes zero AND the point estimate exceeds
        #                  the margin: a real difference worth reporting
        #   inconclusive — CI wider than the margin: underpowered, says
        #                  nothing either way
        eq = (abs(r["tost_lo"]) < args.margin and abs(r["tost_hi"]) < args.margin)
        excludes_zero = (r["tost_lo"] > 0) or (r["tost_hi"] < 0)

        # A "different" verdict additionally requires enough samples for the
        # claim to be defensible, and a distribution-free test that agrees.
        #
        # Observed failure this guard prevents: RSA-2048 keygen at n=3 vs n=3
        # gave board1 74 s and board2 268 s, and the Welch 90% CI excluded
        # zero -- so the two tests above alone returned "different" at +261%.
        # It is not a board difference. Keygen cost is set by how many random
        # candidates fail primality, a heavy-tailed draw that normal-theory
        # intervals do not describe at n=3; Campaign A's five samples on a
        # SINGLE board span 46-303 s, and both boards' means fall inside that
        # range. The exact permutation test gives p=0.100, which is the
        # smallest value C(6,3) can produce -- at this n, significance is
        # unreachable even with perfect separation.
        mw_p = float("nan")
        if len(x) >= 3 and len(y) >= 3:
            try:
                mw_p = stats.mannwhitneyu(x, y, alternative="two-sided")[1]
            except ValueError:
                pass
        well_powered = (len(x) >= MIN_N_FOR_DIFFERENCE
                        and len(y) >= MIN_N_FOR_DIFFERENCE)
        nonparametric_agrees = (mw_p == mw_p) and mw_p < 0.05

        if not informative:
            verdict = "n/a"
        elif eq:
            verdict = "equivalent"
        elif (excludes_zero and abs(r["diff_pct"]) >= args.margin
              and well_powered and nonparametric_agrees):
            verdict = "different"
        else:
            verdict = "inconclusive"

        rows.append(dict(
            algorithm=k[0], operation=k[1], security_level=k[2],
            n1=len(x), n2=len(y),
            mean1_us=x.mean(), mean2_us=y.mean(),
            cv1_pct=cv1, cv2_pct=cv2,
            diff_pct=r["diff_pct"], ci95_lo=r["ci_lo"], ci95_hi=r["ci_hi"],
            tost90_lo=r["tost_lo"], tost90_hi=r["tost_hi"],
            p_welch=r["p"], informative=informative,
            verdict=verdict, equivalent=(verdict == "equivalent"),
        ))

    res = pd.DataFrame(rows)
    csv_path = os.path.join(outdir, "inter_unit_comparison.csv")
    res.to_csv(csv_path, index=False)

    inf = res[res.informative]
    eqv = inf[inf.verdict == "equivalent"]
    diff = inf[inf.verdict == "different"]
    incon = inf[inf.verdict == "inconclusive"]
    worst = eqv.loc[eqv.diff_pct.abs().idxmax()] if len(eqv) else None

    print(f"{'operation':34s} {'board1':>10s} {'board2':>10s} "
          f"{'diff%':>8s} {'90% CI':>18s}  verdict")
    for _, r in res.iterrows():
        name = f"{r.algorithm} {r.operation} {r.security_level}"
        print(f"{name:34s} {r.mean1_us:10.0f} {r.mean2_us:10.0f} "
              f"{r.diff_pct:+8.3f} "
              f"[{r.tost90_lo:+7.3f},{r.tost90_hi:+7.3f}]  {r.verdict}")

    summary = {
        "board1_unique_id": id1, "board2_unique_id": id2,
        "clk_sys_board1_hz": clk1, "clk_sys_board2_hz": clk2,
        "equivalence_margin_pct": args.margin,
        "n_operations": int(len(res)),
        "n_informative": int(len(inf)),
        "n_equivalent": int(len(eqv)),
        "n_different": int(len(diff)),
        "n_inconclusive": int(len(incon)),
        "inconclusive_operations": [
            f"{r.algorithm} {r.operation} {r.security_level}"
            for _, r in incon.iterrows()],
        "different_operations": [
            {"operation": f"{r.algorithm} {r.operation} {r.security_level}",
             "diff_pct": float(r.diff_pct),
             "ci90": [float(r.tost90_lo), float(r.tost90_hi)]}
            for _, r in diff.iterrows()],
        "all_powered_equivalent": bool(len(eqv) and len(diff) == 0),
        "max_abs_diff_pct_equivalent": (
            float(eqv.diff_pct.abs().max()) if len(eqv) else None),
        "max_abs_diff_operation": (
            f"{worst.algorithm} {worst.operation} {worst.security_level}"
            if worst is not None else None),
        "widest_ci_pct_equivalent": float(
            np.max(np.abs(eqv[["tost90_lo", "tost90_hi"]].values))) if len(eqv) else None,
    }
    with open(os.path.join(outdir, "inter_unit_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    print()
    if len(diff) == 0 and len(eqv):
        print(f"RESULT: all {len(eqv)} adequately powered operations are "
              f"equivalent within +/-{args.margin}%.")
        print(f"  Largest observed difference: "
              f"{summary['max_abs_diff_pct_equivalent']:.3f}% "
              f"({summary['max_abs_diff_operation']}).")
        print(f"  Every 90% CI lies within "
              f"+/-{summary['widest_ci_pct_equivalent']:.3f}%.")
        print("\n  Paper claim supported: the two units agree to well within "
              "the margin\n  that could affect any engineering conclusion.")
    elif len(diff):
        print(f"RESULT: {len(diff)} of {len(inf)} operations differ by more "
              f"than +/-{args.margin}%:")
        for _, r in diff.iterrows():
            print(f"  {r.algorithm} {r.operation} {r.security_level}: "
                  f"{r.diff_pct:+.3f}% "
                  f"[{r.tost90_lo:+.3f},{r.tost90_hi:+.3f}]")
        print("\n  This is a real finding, not a failure — report it as "
              "measured inter-unit\n  variation and revise the paper's "
              "single-unit argument accordingly.")
    else:
        print("RESULT: no operation had enough power to conclude anything.")

    if len(incon):
        print(f"\n  {len(incon)} operation(s) inconclusive — interval wider "
              f"than the margin,\n  so they support neither equivalence nor "
              f"difference (low n by design):")
        for _, r in incon.iterrows():
            print(f"    {r.algorithm} {r.operation} {r.security_level} "
                  f"(n={r.n1}/{r.n2}): "
                  f"[{r.tost90_lo:+.2f},{r.tost90_hi:+.2f}]")
        print("  Report these as untested rather than as agreement.")

    print(f"\n  {csv_path}")
    print(f"  {os.path.join(outdir, 'inter_unit_summary.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
