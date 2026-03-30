# Local Host Tests

Desktop-hosted sanity tests that run the same PQClean implementations
on your development machine (without RP2040 hardware). These verify
functional correctness and provide a rough timing baseline for
comparison.

## Building (MinGW / GCC on Windows or Linux)

```bash
cd local_test
mkdir build && cd build
cmake ..
make
```

## Files

- `bench_mlkem_local.c` — ML-KEM-512/768/1024 keygen + encaps + decaps with correctness checks
- `bench_mldsa_local.c` — ML-DSA-44/65/87 keygen + sign + verify with correctness checks
- `bench_harness_local.h` — Timing framework (uses `QueryPerformanceCounter` on Windows, `clock_gettime` on Linux)
- `CMakeLists.txt` — Build configuration
- `compat/` — MinGW compatibility shim

## Purpose

These tests confirm that the PQClean reference C implementations
produce correct results (shared secrets match, signatures verify)
before cross-compiling for the RP2040. They do **not** produce
benchmark numbers comparable to the paper — the RP2040 measurements
are the authoritative data source.
