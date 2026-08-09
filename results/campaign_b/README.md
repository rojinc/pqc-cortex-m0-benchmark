# Campaign B — independent replication (RP2040)

`rp2040_campaign_b.csv` is the independent replication campaign reported in the
paper's *Replication Campaign and Tail Behaviour* section.

## Why it exists

Campaign A (`../raw/`, n=30 deterministic / n=100 signing) is the paper's primary
dataset. Campaign B was captured **for a separate multi-platform study**, on the
same physical RP2040 board but with a **separately written harness**, a different
SDK version, and a different optimisation level. It was not conducted to support
this paper, which is what makes it useful as a replication: it carries no
experimenter bias toward these conclusions.

## Capture provenance

Copied verbatim from the capture log header:

```
# Platform: Raspberry Pi Pico (RP2040, Cortex-M0+)
# CPU: 125 MHz (measured: clk_sys = 125000000 Hz)
# SRAM: 264 KB, Flash: 2 MB
# Paintable stack: 196472 bytes (SP=2003ff78, StackLimit=20010000)
# Sample sizes: deterministic=1000, signing=10000
# Build: Jul 28 2026 20:53:59 | gcc 12.2.1 20230214 | timer=time_us_32 (1us wall clock)
# Msg: 118 bytes
```

| | Campaign A | Campaign B |
|---|---|---|
| Harness | `src/bench_harness.h` (fixed array) | separate implementation (streaming Welford) |
| Optimisation | `-O3` (CMake `Release` default) | `-Os` pinned per translation unit |
| SDK | pico-sdk (campaign A vintage) | pico-sdk 2.2.0 |
| Deterministic n | 30 | 1000 |
| Signing n | 100 | 10,000 |
| Clock | 125 MHz | 125 MHz (read from `clk_sys` at boot) |

## Scope of this file

Filtered to **only the operations the paper cites**: ML-KEM-512 (keygen, encaps,
decaps) and ML-DSA-44 (keygen, sign, verify) — 15,000 rows. The parent campaign
also covered ESP32 and three further schemes; those belong to the separate study
and are not republished here.

## Columns

`algorithm, operation, security_level, time_us, run_number` — one row per
individual operation, identical schema to `../raw/*.csv`. Times are microseconds
from a 1 µs wall clock; cycle counts anywhere in the paper are *derived*
(µs × 125), never directly measured.

## Reproducing the paper's replication numbers

```bash
python scripts/verify_campaign_b.py
```

That script recomputes every campaign-B figure in the paper's replication and
tail tables directly from this CSV and checks them against the published values.
