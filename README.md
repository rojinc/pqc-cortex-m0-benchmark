[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19393777.svg)](https://doi.org/10.5281/zenodo.19393777)
# PQC Benchmarks on ARM Cortex-M0+ (RP2040)

> **Paper:** [Benchmarking NIST-Standardised ML-KEM and ML-DSA on ARM Cortex-M0+: Performance, Memory, and Energy on the RP2040](https://arxiv.org/abs/2603.19340)

Systematic benchmarking of **NIST-standardized ML-KEM (FIPS 203)** and **ML-DSA (FIPS 204)** on ARM Cortex-M0+ (RP2040), with classical baselines (RSA-2048, ECDSA P-256, ECDH P-256).

This repository provides benchmark firmware, reproducibility scripts, and processed datasets for the above paper.

## Author

**Rojin Chhetri** ([ORCID: 0009-0005-2757-3436](https://orcid.org/0009-0005-2757-3436))
Independent Researcher

## Key Results (RP2040 @ 133 MHz)

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
│   ├── raw/                  # Current benchmark CSVs + full logs
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
