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
  -DCMAKE_C_COMPILER=arm-none-eabi-gcc \
  -DCMAKE_CXX_COMPILER=arm-none-eabi-g++
make -j"$(nproc)"
```

Windows (MinGW):

```bash
PICO_SDK_PATH=../pico-sdk cmake .. -G "MinGW Makefiles" -DPICO_NO_PICOTOOL=1 \
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

## Notes on expected variability

- Deterministic operations (e.g., ML-KEM encaps/decaps) should match closely across runs.
- ML-DSA signing and RSA-2048 key generation are inherently variable and should be interpreted using distribution metrics (CV, p95, p99), not single-run values.
