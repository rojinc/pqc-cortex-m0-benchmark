[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19393777.svg)](https://doi.org/10.5281/zenodo.19393777)
# PQC Benchmarks on ARM Cortex-M0+ (RP2040)

> **Paper:** [Benchmarking NIST-Standardised ML-KEM and ML-DSA on ARM Cortex-M0+: Performance, Memory, and Energy on the RP2040](https://arxiv.org/abs/2603.19340)

Systematic benchmarking of **NIST-standardized ML-KEM (FIPS 203)** and **ML-DSA (FIPS 204)** on ARM Cortex-M0+ (RP2040), with classical baselines (RSA-2048, ECDSA P-256, ECDH P-256).

This repository provides benchmark firmware, reproducibility scripts, and processed datasets for the above paper.

## Author

**Rojin Chhetri** ([ORCID: 0009-0005-2757-3436](https://orcid.org/0009-0005-2757-3436))
Independent Researcher

## Key Results (RP2040 @ 125 MHz, `-O3`)

> Measured at the pico-sdk default `clk_sys` of **125 MHz**. 133 MHz is the
> RP2040 datasheet maximum, not this configuration. Wall-clock timings below are
> measured directly; cycle counts quoted anywhere are *derived* (µs × 125).
> Firmware is built at **`-O3`**, now pinned explicitly in `CMakeLists.txt`.

### ML-KEM timing (mean, µs)

| Level | Keygen | Encaps | Decaps | Full Handshake |
|-------|--------|--------|--------|----------------|
| 512   | 9,945  | 11,531 | 14,233 | **35.7 ms** |
| 768   | 16,020 | 18,580 | 22,016 | **56.6 ms** |
| 1024  | 25,181 | 28,097 | 32,450 | **85.7 ms** |

### ML-DSA timing (mean, µs)

| Level | Keygen | Sign (mean) | Sign (p99) | Verify |
|-------|--------|-------------|------------|--------|
| 44    | 39,833 | 158,907 | ~490,000 | 43,977 |
| 65    | 68,420 | 256,617 | ~954,000 | 72,206 |
| 87    | 114,294| 355,232 | ~1,125,000 | 120,226 |

### Classical baselines (mean, µs)

| Algorithm | Operation | Time |
|-----------|-----------|------|
| RSA-2048 | keygen | 215,611,503 (~216 s) |
| RSA-2048 | encrypt | 139,681 |
| RSA-2048 | decrypt | 3,392,897 |
| ECDSA-P256 | keygen | 83,637 |
| ECDSA-P256 | sign | 92,597 |
| ECDSA-P256 | verify | 321,359 |
| ECDH-P256 | key agreement | 617,026 |

## Independent Replication (Campaign B)

`results/campaign_b/` holds an independent replication of the ML-KEM-512 and
ML-DSA-44 measurements: **n=1000** per deterministic operation and **n=10,000**
signatures, captured with a separately written harness at `-Os` for an unrelated
multi-platform study. It was not run to support this paper, which is what makes
it useful as a check.

| | Campaign A (primary) | Campaign B (replication) |
|---|---|---|
| Signing samples | 100 | 10,000 |
| Optimisation | `-O3` | `-Os` |
| Harness | `src/bench_harness.h` | separate implementation |

**What replicates:** every ordering and ratio the paper's conclusions rest on.
**What shifts:** absolute latencies are 4–16% higher at `-Os`.

**The signing tail was materially understated at n=100.** The 100-sample
campaign put the p99 at 490 ms and never observed anything past 542 ms; at
n=10,000 the p99 is 584 ms and the worst case is **1157 ms — 14.4× the fastest
signature.** Any duty-cycle or watchdog budget for ML-DSA signing on this class
of part should be set from the large-sample tail.

## Inter-Unit Agreement (Campaign C)

Campaigns A and B both ran on one physical RP2040, so they bound *build*
sensitivity but say nothing about manufacturing spread. `results/campaign_c/`
holds a two-device comparison under one firmware build: 28 operations across
ML-KEM, ML-DSA, RSA-2048, ECDSA/ECDH-P256 and the on-chip RNG, 58,206 timed runs
across both units.

Equivalence was tested with TOST against a **pre-declared ±1% margin** — a
non-significant difference is not evidence of agreement, so the interval has to
fall inside the margin rather than merely cover zero.

| | result |
|---|---|
| Adequately powered operations | 23 of 28 |
| **Equivalent within ±1%** | **23 (all of them)** |
| Different | 0 |
| Largest difference observed | 0.300% (ECDSA-P256 verify) |
| Largest among the 15 PQC operations | 0.075% (ML-DSA-44 keygen) |
| Inconclusive (low n by design) | 2 — reported as untested, not as agreement |

**Build configuration matters ~26× more than which board you use.** Across the
15 deterministic PQC operations common to campaigns A and C, changing
optimisation level and SDK version moves mean latency by 1.4–2.5%; changing the
physical die moves it by at most 0.075%. Always report the build alongside an
absolute figure.

Two operations report `inconclusive` rather than agreement. RSA-2048 keygen runs
at n=3 by design (~3 min each): with 3-vs-3 samples a permutation test has a
*minimum attainable* p of 0.100, so no difference can reach significance however
the data fall. Single-byte RNG generation is quantised to the 1 µs timer at a
mean of 1 µs, so its interval reflects timer resolution, not hardware.

```bash
python scripts/compare_boards.py            # TOST equivalence across both units
```

Verify every published number directly from the raw data. Both scripts exit
non-zero on any mismatch:

```bash
python scripts/verify_campaign_b.py         # campaign-B tables and lattice fit
python scripts/verify_revision.py --fast    # revision analyses, seconds
python scripts/verify_revision.py           # adds the identifiability section (~18 min)
```

## Repository Layout

```text
.
├── CMakeLists.txt            # RP2040 benchmark firmware build
├── memmap_custom.ld          # Custom linker script (stack in main RAM)
├── REPRODUCE.md              # Full reproduction workflow
├── AUTHORS.md                # Author/contributor metadata
├── CITATION.cff              # Citation metadata for GitHub/Zenodo
├── requirements.txt          # Python dependency pin ranges
├── src/                      # Firmware benchmark sources
├── scripts/                  # Data capture + analysis scripts
├── results/                  # Published benchmark data
│   ├── raw/                  # Campaign A: benchmark CSVs + full logs
│   ├── campaign_b/           # Campaign B: independent replication (n=10,000 signing)
│   ├── campaign_c/           # Campaign C: two-device inter-unit comparison
│   └── old_data/             # Historical runs + environment metadata
└── local_test/               # Host-local sanity tests without hardware
```

## Quick Start (Build Firmware)

Clone repositories:

```bash
git clone https://github.com/rojinc/pqc-cortex-m0-benchmark.git PQC-research
cd PQC-research

git clone https://github.com/PQClean/PQClean.git pqclean
cd pqclean && git checkout 3730b32a && cd ..

git clone https://github.com/raspberrypi/pico-sdk.git
cd pico-sdk && git checkout 2.2.0 && git submodule update --init && cd ..
```

Build:

```bash
mkdir -p build
cd build

# Linux/macOS
PICO_SDK_PATH=../pico-sdk cmake .. \
  -DCMAKE_C_COMPILER=arm-none-eabi-gcc \
  -DCMAKE_CXX_COMPILER=arm-none-eabi-g++
make -j"$(nproc)"

# Windows (MinGW)
# PICO_SDK_PATH=../pico-sdk cmake .. -G "MinGW Makefiles" -DPICO_NO_PICOTOOL=1 \
#   -DCMAKE_C_COMPILER=arm-none-eabi-gcc -DCMAKE_CXX_COMPILER=arm-none-eabi-g++
# mingw32-make -j4
```

Convert ELF to UF2:

```bash
python ../scripts/elf2uf2.py bench_mlkem.elf bench_mlkem.uf2
python ../scripts/elf2uf2.py bench_mldsa.elf bench_mldsa.uf2
python ../scripts/elf2uf2.py bench_classical.elf bench_classical.uf2
```

For full data collection, validation, and statistical comparison, see [REPRODUCE.md](REPRODUCE.md).

## Python Environment

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## How to Cite

```bibtex
@article{chhetri2026benchmarking,
  author  = {Rojin Chhetri},
  title   = {Benchmarking Post-Quantum Cryptography on Resource-Constrained
             IoT Devices: ML-KEM and ML-DSA on ARM Cortex-M0+},
  year    = {2026},
  eprint  = {2603.19340},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CR}
}
```

## License

MIT — see [LICENSE](LICENSE).
