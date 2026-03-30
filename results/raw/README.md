# Raw Benchmark Data

These CSV files contain the raw benchmark measurements from the RP2040
(ARM Cortex-M0+ at 133 MHz). Each file was captured via UART from a
single authoritative measurement run.

## Files

| File | Paper Table | Contents |
|------|-------------|----------|
| `mlkem_pico.csv` | Table II | ML-KEM-512/768/1024 keygen, encaps, decaps (30 runs each) |
| `mldsa_pico.csv` | Table III | ML-DSA-44/65/87 keygen, sign, verify (30/100/30 runs) |
| `classical_pico.csv` | Table IV | RSA-2048, ECDSA P-256, ECDH P-256 (30 runs; RSA keygen: 5 runs) |

## CSV Columns

- `algorithm` — Algorithm name (ML-KEM, ML-DSA, RSA-2048, ECDSA-P256, ECDH-P256)
- `operation` — Operation (keygen, encaps, decaps, sign, verify, encrypt, decrypt, key_agreement)
- `security_level` — Security level (512/768/1024 for ML-KEM; 44/65/87 for ML-DSA; 0 for classical)
- `time_us` — Execution time in microseconds (from `time_us_32()`)
- `energy_uj` — Estimated energy in microjoules (= time_us x 0.0792, datasheet model)

## Full UART Logs

The `*_full.txt` files contain the complete UART output including
diagnostic messages, correctness checks, and stack measurements.

## Preliminary Data

Earlier measurement runs are archived in `../old_data/raw/` for
comparison. See the paper's Data Provenance section (Section IV-F).
