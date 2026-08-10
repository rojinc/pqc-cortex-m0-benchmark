# Campaign C — two-unit comparison runbook

Campaign C answers one reviewer question the paper currently argues rather than
measures: **do two physical RP2040 units produce the same timings?**

It is a **new capture**, not a re-run of Campaign A. Campaign A (n=30 / n=100)
remains the published dataset behind every existing table and figure and is not
modified. Campaign B (the independent-harness replication) is likewise untouched
— its value comes from having been produced by a separately written harness, so
re-running it here would destroy the property that makes it credible.

## Hardware

Buy a second **Raspberry Pi Pico (RP2040)** — part `SC0915`.

**Not the Pico 2.** It is pin-compatible and looks nearly identical, but carries
the RP2350 with Cortex-M33 cores. That is a different core generation, so it is
not a second unit of the same silicon and cannot answer this question.

If possible, buy from a different supplier than board 1, or check the date code.
Two boards from the same reel likely share a wafer lot, which weakens the
inter-unit argument.

## Why both boards

Precision of an inter-unit comparison is limited by the **smaller** of the two
sample sizes. Board 1's Campaign A data is n=30, so pairing it against a fresh
n=1000 capture on board 2 resolves only ~0.20%. Two fresh n=1000 captures
resolve ~0.05% — the same afternoon's work for a fourfold tighter bound.

Capturing both boards fresh also removes a confound: board 1's published data is
older and built against a different SDK version, so any difference would be
partly toolchain, not silicon.

## Protocol

| operation class | n | rationale |
|---|---|---|
| all ML-KEM, ML-DSA keygen/verify, ECDSA, ECDH | 1000 | CV < 1%, this is where inter-unit signal lives |
| ML-DSA sign | 1000 | reported, but rejection sampling dominates its variance |
| RSA-2048 decrypt | 100 | ~3.4 s per sample |
| RSA-2048 keygen | 3 | ~3.6 min per sample |

ML-DSA signing is **not** raised to 10,000. Its CV is ~64% because of rejection
sampling, so even n=10,000 on both boards resolves only 2.7% against 8.5% at
n=1000 — 24 extra minutes per board to move a number that stays drowned in
algorithmic variance either way.

## Time

Measured from Campaign A's own per-operation means, plus the 10 ms inter-row USB
delay:

| firmware | rows | execution | USB delay | total |
|---|---|---|---|---|
| `bench_mlkem` | 9,000 | 3.0 min | 1.5 min | **4.5 min** |
| `bench_mldsa` | 9,000 | 20.5 min | 1.5 min | **22.0 min** |
| `bench_classical` | 5,103 | 37.3 min | 0.9 min | **38.2 min** |
| `bench_rng` | 6,000 | 0.1 min | 1.0 min | **1.1 min** |

**~66 min per board, ~2h 12m for both**, plus a few minutes of handling per
flash. Run it unattended — the capture script stops on its own.

`bench_classical` is the long pole, and RSA-2048 keygen (10.8 min) and ECDH
key agreement (10.3 min) are half of it. If you want it shorter, drop RSA keygen
to n=1 with `-DBENCH_N_RSA_KEYGEN=1`: it is a classical baseline, not a headline
number, and it is already reported as underpowered.

## Build

```bash
cd pqc-cortex-m0-benchmark
mkdir -p build-campaign-c && cd build-campaign-c
cmake -DBENCH_N=1000 -DBENCH_N_SIGN=1000 \
      -DBENCH_N_RSA_DEC=100 -DBENCH_N_RSA_KEYGEN=3 ..
make -j4
```

Produces `bench_mlkem.uf2`, `bench_mldsa.uf2`, `bench_classical.uf2`,
`bench_rng.uf2`.

**An unmodified `cmake ..` still reproduces Campaign A** (n=30 / n=100 / RSA
keygen n=5). The sample counts default to the published values in
`bench_harness.h`; the cache variables only override them when passed.

## Capture

Once per firmware image per board. Hold BOOTSEL, plug in, copy the `.uf2`, wait
for it to reboot, then:

```bash
python scripts/capture_campaign_c.py --list-ports          # find the port

python scripts/capture_campaign_c.py --port /dev/ttyACM0 \
    --board 1 --firmware mlkem
```

Repeat for `mldsa`, `classical`, `rng`, then all four again with `--board 2`.
Output lands in `results/campaign_c/board<N>/`.

The script stops on the firmware's completion marker, so it needs no
supervision. It exits non-zero if the capture is short — check the exit code
rather than eyeballing the output. Re-run any firmware that reports a shortfall
before using its data.

Each capture writes three files: the parsed CSV, the verbatim serial log, and a
`_meta.json` recording the board's unique hardware ID, measured `clk_sys`, and
firmware build stamp. **The unique ID is what proves the two captures came from
two different physical boards** — without it the comparison is unfalsifiable,
and the analysis script refuses to run.

## Analysis

```bash
python scripts/compare_boards.py
```

Writes `results/campaign_c/inter_unit_comparison.csv` and
`inter_unit_summary.json`.

The analysis is an **equivalence** test (TOST at a ±1% margin), not a difference
test. This matters: at n=1000 per board, a 0.05% difference becomes
"statistically significant" while being physically irrelevant, so a plain
significance test would appear to argue against the paper for no good reason.
Equivalence lets the result be stated as a positive finding — the units agree to
within X% — rather than as a failure to reject.

The ±1% margin is declared in advance rather than tuned after seeing the data:
it is the level below which an inter-unit difference could not change any
engineering conclusion, since timer quantisation and optimisation-level effects
in the paper are already larger.

Each operation gets one of four verdicts:

- **equivalent** — CI inside the margin; the units agree
- **different** — CI excludes zero *and* the point estimate exceeds the margin
- **inconclusive** — CI wider than the margin; underpowered, says nothing
  either way (RSA keygen at n=3 lands here by construction)
- **n/a** — ML-DSA signing, excluded from the claim because rejection sampling
  dominates its variance

The distinction between *different* and *inconclusive* is the point: reporting a
low-n operation as "not equivalent" would be a false alarm, and reporting it as
agreement would overclaim.

## Writing it up

Two units can refute "units vary substantially"; they are **not** a
silicon-variation study. Write the result as measured agreement between two
specific units, and do not generalise to the population of RP2040 parts. If both
boards come from the same wafer lot, say so.

If the result comes back **different** rather than equivalent, that is a
publishable finding too — report the measured inter-unit variation and revise
the single-unit argument accordingly. Do not re-run until it agrees.

## The RNG check

`bench_rng` addresses the separate reviewer item about `randombytes()`. The
paper argues random-byte generation cannot contribute to timing variance because
it is called a fixed number of times per operation — which silently assumes each
call costs the same regardless of ring-oscillator state. This firmware times the
call in isolation at 1, 32, and 64 bytes so the assumption is measured instead
of asserted: near-constant timing that scales linearly in request size supports
it; elevated CV or a heavy upper tail refutes it.
