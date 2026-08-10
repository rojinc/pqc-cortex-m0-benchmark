/*
 * bench_rng.c — Direct timing of the ROSC-backed randombytes() on RP2040
 *
 * Why this exists
 * ---------------
 * The paper argues that random-byte generation does not contribute to the
 * observed timing variance, because randombytes() is called a fixed number
 * of times per cryptographic operation. That argument silently assumes each
 * *call* costs the same regardless of the ring oscillator's state. This
 * benchmark tests that assumption directly instead of asserting it.
 *
 * The implementation under test reads rosc_hw->randombit one bit at a time
 * and shifts eight of them into a byte, so the expected cost is a fixed
 * number of register reads per byte with no rejection, no retry, and no
 * dependence on an entropy pool. If that is right, the timing should be
 * near-constant and linear in the request size. If instead the ROSC stalls
 * or the bit register gates on anything state-dependent, it will show up
 * here as elevated CV or a heavy upper tail.
 *
 * Request sizes cover what the PQC operations actually ask for:
 *   32 bytes  — ML-KEM seed / ML-DSA rho, the dominant call size
 *   64 bytes  — ML-KEM keypair coins
 *   1 byte    — smallest call, isolates per-call overhead from per-byte cost
 *
 * Output shares the standard CSV schema so parse_serial.py needs no changes.
 * "security_level" carries the request size in bytes, which is a mild abuse
 * of the column but keeps one schema across every capture.
 */

#include "bench_harness.h"
#include "randombytes.h"

#ifndef RNG_SIZES
#define RNG_SIZES { 1, 32, 64 }
#endif

int main(void) {
    bench_init();
    bench_csv_header();

    printf("# --- randombytes() isolation timing (ROSC) ---\n");
    printf("# Answers: does a single randombytes() call take constant time,\n");
    printf("# or does it vary with ring-oscillator state?\n");

    static const size_t sizes[] = RNG_SIZES;
    static uint8_t buf[64];

    for (size_t _s = 0; _s < sizeof(sizes) / sizeof(sizes[0]); _s++) {
        size_t nbytes = sizes[_s];

        /*
         * Warm up briefly so the first sample does not carry one-off costs
         * (first touch of the ROSC registers, instruction cache effects).
         * Discarded, not recorded.
         */
        for (int _w = 0; _w < 16; _w++) randombytes(buf, nbytes);

        BENCH_RUN_EXTENDED("randombytes", "generate", (int)nbytes,
                           NUM_RUNS_RNG, {
            randombytes(buf, nbytes);
        });
    }

    /*
     * Per-byte cost is the useful cross-check: if the 1/32/64-byte means are
     * consistent with a fixed per-byte cost, the routine is linear and
     * state-independent, which is exactly the paper's claim.
     */
    printf("# Compare the three means: linear scaling in request size with\n");
    printf("# low CV supports the constant-time-per-call assumption.\n");
    printf("# === randombytes benchmark complete ===\n");

    while (true) {
        sleep_ms(10000);
    }
    return 0;
}
