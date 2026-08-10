# Reproducing the Experiments

This guide reproduces the firmware build, data capture, and data validation pipeline used in the manuscript.

## 1) Prerequisites

### Hardware
- Raspberry Pi Pico or Pico H (RP2040)
- Data-capable micro-USB cable

### Software
- Python 3.10+
- arm-none-eabi-gcc (tested with 12.2.1)
- CMake 3.20+
- Make / MinGW Make

Install Python dependencies:

```bash
pip install -r requirements.txt
```

## 2) Clone and pin dependencies

```bash
git clone https://github.com/rojinc/pqc-cortex-m0-benchmark.git PQC-research
cd PQC-research

git clone https://github.com/PQClean/PQClean.git pqclean
cd pqclean && git checkout 3730b32a && cd ..

git clone https://github.com/raspberrypi/pico-sdk.git
cd pico-sdk && git checkout 2.2.0 && git submodule update --init && cd ..
```

## 3) Record environment fingerprint

```bash
python scripts/reproduce.py fingerprint
```

This writes `results/environment.json`.

## 4) Build benchmark firmware

```bash
mkdir -p build
cd build
```

Linux/macOS:

```bash
PICO_SDK_PATH=../pico-sdk cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=arm-none-eabi-gcc \
  -DCMAKE_CXX_COMPILER=arm-none-eabi-g++
make -j"$(nproc)"
```

> **Optimisation level matters.** The published numbers are `-O3`
> (`CMAKE_BUILD_TYPE=Release`). `CMakeLists.txt` now defaults to `Release` and
> prints the flags it used, so an omitted build type no longer silently produces
> an `-O0` build with several-fold higher latencies. Confirm the configure step
> prints:
>
> ```
> -- Build type: Release (C flags: -O3 -DNDEBUG)
> ```
>
> Building at `-Os` instead (`-DCMAKE_BUILD_TYPE=MinSizeRel`) is legitimate but
> gives 4–16% higher latency — see `results/campaign_b/`.

> **`-DNDEBUG` disables `assert()`, and nothing in this firmware uses it.**
> Release mode adds `-DNDEBUG`, so it is worth stating what that does *not*
> switch off here. Auditing every translation unit in the firmware link — our
> `src/*.c` and `src/*.h`, plus the PQClean files named in `CMakeLists.txt`
> (ML-KEM-512/768/1024 and ML-DSA-44/65/87 `clean/`, and `common/fips202.c`,
> `common/sha2.c`, `common/sp800-185.c`) — finds zero occurrences of
> `assert(`, `static_assert`, or `<assert.h>`. The only PQClean file at the
> pinned commit that uses `assert()` is `common/randombytes.c`, which targets
> desktop operating systems and is deliberately **not** compiled: it is
> replaced by `src/randombytes_pico.c` (see the comment at `CMakeLists.txt`
> line 38). No correctness check is therefore compiled out by `-DNDEBUG`.
>
> Algorithm correctness is established separately, before cross-compilation:
> PQClean's KAT vectors are validated on the host, and the firmware itself
> asserts nothing at runtime. Verify with:
>
> ```bash
> grep -rn "assert" src/ pqclean/crypto_kem/*/clean/ \
>   pqclean/crypto_sign/*/clean/ pqclean/common/fips202.c \
>   pqclean/common/sha2.c pqclean/common/sp800-185.c
> ```

Windows (MinGW):

```bash
PICO_SDK_PATH=../pico-sdk cmake .. -G "MinGW Makefiles" -DPICO_NO_PICOTOOL=1 \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=arm-none-eabi-gcc \
  -DCMAKE_CXX_COMPILER=arm-none-eabi-g++
mingw32-make -j4
```

If CMake cannot find the SDK, provide an absolute path, e.g.:

```bash
PICO_SDK_PATH=/absolute/path/to/pico-sdk cmake ..
```

Convert artifacts to UF2:

```bash
python ../scripts/elf2uf2.py bench_mlkem.elf bench_mlkem.uf2
python ../scripts/elf2uf2.py bench_mldsa.elf bench_mldsa.uf2
python ../scripts/elf2uf2.py bench_classical.elf bench_classical.uf2
cd ..
```

## 5) Capture benchmark data from serial

Run one benchmark at a time:

1. Hold **BOOTSEL** and connect Pico USB.
2. Copy one UF2 file to the `RPI-RP2` drive.
3. Wait for reboot; identify serial port.
4. Capture CSV.

Example commands:

```bash
python scripts/parse_serial.py --port COM4 --output results/my_run/mlkem_pico.csv
python scripts/parse_serial.py --port COM4 --output results/my_run/mldsa_pico.csv
python scripts/parse_serial.py --port COM4 --output results/my_run/classical_pico.csv
```

(Replace `COM4` with your serial device, e.g., `/dev/ttyACM0`.)

Guided alternative:

```bash
python scripts/reproduce.py collect --port COM4 --run-id my_run
```

## 6) Post-process and validate

```bash
python scripts/add_energy.py --dir results/my_run
python scripts/validate_data.py --dir results/my_run
python scripts/reproduce.py compare --run1 results/raw --run2 results/my_run
```

Outputs:
- `results/my_run/*.csv` processed with energy estimates
- comparison JSON reports in `results/`

## 7) Verify the published replication numbers

No hardware required — this recomputes every campaign-B value in the paper
straight from the archived raw data and fails loudly on any mismatch:

```bash
python scripts/verify_campaign_b.py
```

It checks the replication table, the signing-tail quantiles, and the
rejection-sampling lattice fit (iteration step *c*, early-abort quantum *f*, and
the recovered iteration counts against the E[k]=4.25 predicted by FIPS 204).

## 8) Verify the revision analyses

A second script covers the analyses added during peer review, again from
archived data only:

```bash
python scripts/verify_revision.py          # full run, about 18 minutes
python scripts/verify_revision.py --fast   # skips the slow section, seconds
```

It reproduces:

1. The **negative identifiability result** of Section V-E. It shows that the
   RMS objective alone does not determine the iteration step *c*, that the
   modal-structure anchoring recovers the published n=10,000 fit
   (c=28.91 ms, f=5.91 ms) without being told either value, and that the same
   procedure applied to the n=100 samples returns bootstrap intervals for
   E[k] too wide to support any cross-level claim. This section carries the
   bootstrap and is what makes the full run slow; `--fast` skips it.
2. The **corrected chi-squared test**, on the parameter estimated from the
   sample rather than the FIPS-fixed one, alongside a reproduction of the
   original construction whose rejection the paper retracts.
3. The **robustness and power analysis** backing that non-rejection, since a
   non-rejection is weak evidence on its own: the minimum expected bin count
   (59, well clear of the usual expected-count-under-5 concern), an exact
   parametric-bootstrap p-value that uses no asymptotic approximation
   (p=0.070 against the asymptotic 0.066), a Kolmogorov-Smirnov check
   calibrated the same way (p=0.51), and a power curve against a
   beta-geometric alternative. The last one is the useful number: the test
   reaches 80% power at beta=0.988, so this campaign rules out departures
   that would inflate E[k] by more than about 4.4%, and cannot rule out
   smaller ones.
4. The **synthetic control** refuting bin misassignment as an explanation for
   that rejection, including the noise sweep.
4. The **timer-quantisation bound** and all three confidence intervals for the
   worst case (bootstrap, Student-*t*, normal), so the 0.60% figure the paper
   quotes is attributable to a named method rather than ambiguous.
5. The **Cortex-M4 comparison**, including the slowdown ratios and the pqm4
   commit the reference cycle counts come from.
6. Every **millisecond/kilocycle pair** in the paper, checked against the
   RP2040's actual 125 MHz core clock. A figure computed at the 133 MHz
   datasheet maximum once survived into the ECDH prose, so this section
   checks the conversion everywhere it appears rather than only where the
   error was found.

Both scripts exit non-zero if any published number fails to reproduce.

## Notes on expected variability

- Deterministic operations (e.g., ML-KEM encaps/decaps) should match closely across runs.
- ML-DSA signing and RSA-2048 key generation are inherently variable and should be interpreted using distribution metrics (CV, p95, p99), not single-run values.
- **Sample size drives the signing tail.** At n=100 the observed maximum sits
  near the p99 and understates the true worst case by roughly 2×. The paper's
  tail claims come from the n=10,000 campaign in `results/campaign_b/`; do not
  size a watchdog or duty-cycle budget from a short run.
- **Absolute latency is optimisation-dependent.** `-Os` firmware runs 4–16%
  slower than the published `-O3` numbers. Compare like with like.
- **A different board is not a source of disagreement; a different build is.**
  Campaign C (`results/campaign_c/`) measured two physical RP2040 units under
  one firmware image and found all 23 adequately powered operations equivalent
  within ±1%, PQC operations agreeing to 0.075%. The optimisation-level effect
  above is ~26× larger. If your numbers differ from the published ones by more
  than ~0.1% on a deterministic PQC operation, check the build before suspecting
  the hardware.
