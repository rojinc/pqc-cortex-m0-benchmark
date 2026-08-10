/*
 * bench_harness.h — Timing measurement framework for PQC benchmarks
 *
 * Uses time_us_32() from the Pico SDK to measure operations in microseconds.
 * Runs each operation NUM_RUNS times, computes mean/min/max/stddev,
 * and prints CSV output over USB serial.
 *
 * CSV format: algorithm,operation,security_level,time_us,run_number
 */

#ifndef BENCH_HARNESS_H
#define BENCH_HARNESS_H

#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include "pico/stdlib.h"
#include "pico/unique_id.h"
#include "hardware/timer.h"
#include "hardware/clocks.h"

/*
 * Sample counts. Both are overridable at compile time so the same sources
 * build Campaign A (the published dataset, n=30 / n=100) and Campaign C
 * (the two-unit comparison, n=1000). Defaults MUST stay 30/100 so that
 * Campaign A reproduces byte-for-byte from an unmodified checkout.
 *
 *   Campaign A:  cmake ..                                  (defaults)
 *   Campaign C:  cmake -DBENCH_N=1000 -DBENCH_N_SIGN=1000  ..
 */
#ifndef NUM_RUNS
#define NUM_RUNS       30
#endif
#ifndef NUM_RUNS_DSA_SIGN
#define NUM_RUNS_DSA_SIGN 100  /* ML-DSA signing needs more runs for variance analysis */
#endif

/*
 * Delay after each CSV row so the USB CDC stack can drain its buffer.
 * At 10 ms and ~24k rows this adds ~4 min to a Campaign C run; that is
 * cheap insurance against dropped rows, so do not lower it without
 * checking the captured row counts against the expected ones.
 */
#ifndef BENCH_ROW_DELAY_MS
#define BENCH_ROW_DELAY_MS 10
#endif

/*
 * Sample count for the randombytes() isolation benchmark. A single call is
 * microseconds, so a large n costs almost nothing in execution time and the
 * run is dominated by the inter-row USB delay.
 */
#ifndef NUM_RUNS_RNG
#define NUM_RUNS_RNG 2000
#endif

/*
 * RSA-2048 gets its own counts because it is orders of magnitude slower than
 * everything else. Defaults preserve Campaign A exactly: decrypt inherits
 * NUM_RUNS (30), keygen stays at the hard-coded 5 the published run used.
 *
 * Without these, -DBENCH_N=1000 would raise RSA decrypt to 1000 samples at
 * ~3.4 s each — 56 minutes for one operation, roughly doubling the whole
 * capture to tighten a classical baseline that is not the paper's subject.
 */
#ifndef NUM_RUNS_RSA_DEC
#define NUM_RUNS_RSA_DEC NUM_RUNS
#endif
#ifndef NUM_RUNS_RSA_KEYGEN
#define NUM_RUNS_RSA_KEYGEN 5
#endif

/* Stack painting for peak stack usage measurement */
#define STACK_PAINT_VALUE 0xDEADBEEF

/*
 * Print CSV header — call once at program start
 */
static inline void bench_csv_header(void) {
    printf("algorithm,operation,security_level,time_us,run_number\n");
}

/*
 * Print one CSV row
 */
static inline void bench_csv_row(const char *algo, const char *op,
                                  int sec_level, uint32_t time_us,
                                  int run) {
    printf("%s,%s,%d,%lu,%d\n", algo, op, sec_level,
           (unsigned long)time_us, run);
    /* Yield to USB stack so CDC doesn't timeout during long benchmarks */
    sleep_ms(BENCH_ROW_DELAY_MS);
}

/*
 * Run a benchmark: execute `func` NUM_RUNS times, printing CSV each run.
 * Also prints a summary line prefixed with '#' for quick human reading.
 *
 * Usage:
 *   BENCH_RUN("ML-KEM", "keygen", 512, {
 *       OQS_KEM_keypair(kem, pk, sk);
 *   });
 */
#define BENCH_RUN(algo, op, sec_level, code_block)                          \
    BENCH_RUN_EXTENDED(algo, op, sec_level, NUM_RUNS, code_block)

/*
 * Extended run macro with an explicit iteration count.
 *
 * Summary statistics are accumulated with Welford's online algorithm rather
 * than buffered in an array. The array version allocated 4*n bytes on the
 * stack, which is 4 KB at n=1000 and 40 KB at n=10000 — on top of the PQC
 * operation's own stack demand, which for ML-DSA-87 signing is already tens
 * of kilobytes. Streaming keeps the harness's own footprint constant at a
 * few dozen bytes regardless of n, so sample size can no longer push a
 * benchmark into stack overflow.
 *
 * Every individual timing is still emitted as its own CSV row, so the
 * captured data is unchanged; only the '# SUMMARY' line is computed
 * differently. Welford is also the numerically stabler of the two for
 * the large-n case.
 */
#define BENCH_RUN_EXTENDED(algo, op, sec_level, num_runs, code_block)       \
    do {                                                                     \
        const int _n = (num_runs);                                          \
        double _mean = 0.0, _m2 = 0.0;                                      \
        uint32_t _min = UINT32_MAX, _max = 0;                              \
        for (int _i = 0; _i < _n; _i++) {                                   \
            uint32_t _start = time_us_32();                                 \
            { code_block; }                                                 \
            uint32_t _end = time_us_32();                                   \
            uint32_t _dt = _end - _start;  /* wraps correctly < 71.6 min */ \
            bench_csv_row(algo, op, sec_level, _dt, _i + 1);                \
            if (_dt < _min) _min = _dt;                                     \
            if (_dt > _max) _max = _dt;                                     \
            double _delta = (double)_dt - _mean;                            \
            _mean += _delta / (double)(_i + 1);                             \
            _m2   += _delta * ((double)_dt - _mean);                        \
        }                                                                    \
        double _stddev = (_n > 0) ? sqrt(_m2 / (double)_n) : 0.0;           \
        double _cv = (_mean > 0) ? (_stddev / _mean * 100.0) : 0;          \
        printf("# SUMMARY %s %s %d: mean=%.0f min=%lu max=%lu "            \
               "stddev=%.1f cv=%.2f%% (n=%d)\n",                            \
               algo, op, sec_level, _mean,                                   \
               (unsigned long)_min, (unsigned long)_max, _stddev, _cv,       \
               _n);                                                          \
    } while (0)

/*
 * Stack painting: call before the operation to paint the stack
 * with a known pattern, then measure how much was overwritten.
 */
static inline void bench_paint_stack(uint32_t *bottom, size_t size_words) {
    for (size_t i = 0; i < size_words; i++) {
        bottom[i] = STACK_PAINT_VALUE;
    }
}

static inline uint32_t bench_measure_stack(uint32_t *bottom, size_t size_words) {
    size_t unused = 0;
    for (size_t i = 0; i < size_words; i++) {
        if (bottom[i] == STACK_PAINT_VALUE)
            unused++;
        else
            break;
    }
    return (uint32_t)((size_words - unused) * sizeof(uint32_t));
}

/*
 * Measure peak stack usage for a single operation using stack painting.
 * Paints from __StackLimit up to current SP, runs the operation once,
 * then scans for the high-water mark.
 *
 * Usage:
 *   BENCH_STACK("ML-KEM", "keygen", 512, {
 *       PQCLEAN_MLKEM512_CLEAN_crypto_kem_keypair(pk, sk);
 *   });
 */
extern uint32_t __StackLimit;   /* provided by linker script (stack bottom) */

#define BENCH_STACK(algo, op, sec_level, code_block)                         \
    do {                                                                      \
        uint32_t _sp;                                                         \
        __asm__ volatile("mov %0, sp" : "=r"(_sp));                          \
        uint32_t *_bottom = &__StackLimit;                                   \
        size_t _words = (_sp - (uint32_t)_bottom) / sizeof(uint32_t);        \
        size_t _avail = _words * sizeof(uint32_t);                           \
        bench_paint_stack(_bottom, _words);                                   \
        { code_block; }                                                       \
        uint32_t _used = bench_measure_stack(_bottom, _words);               \
        /* Overflow guard: if bottom word was overwritten, stack may have     \
         * grown past __StackLimit and the measurement is unreliable. */      \
        int _overflow = (_bottom[0] != STACK_PAINT_VALUE);                   \
        printf("# STACK %s %s %d: %lu bytes (avail=%lu%s)\n",               \
               algo, op, sec_level, (unsigned long)_used,                     \
               (unsigned long)_avail,                                         \
               _overflow ? " OVERFLOW" : "");                                 \
        if (_overflow)                                                        \
            printf("# WARNING: stack overflow detected — value unreliable, " \
                   "increase PICO_STACK_SIZE\n");                             \
        sleep_ms(10);                                                         \
    } while (0)

/*
 * Wait for USB serial connection before starting benchmarks
 */
static inline void bench_init(void) {
    stdio_init_all();
    /* Wait until USB serial is actually connected by the host */
    while (!stdio_usb_connected()) {
        sleep_ms(100);
    }
    /* Extra settle time for Windows CDC driver */
    sleep_ms(2000);
    printf("# PQC Cortex-M0+ Benchmark Suite\n");
    printf("# Platform: Raspberry Pi Pico (RP2040, ARM Cortex-M0+)\n");

    /*
     * Report the MEASURED system clock, not a datasheet figure. An earlier
     * revision of this header advertised 133 MHz (the RP2040's rated
     * maximum); the SDK default is 125 MHz, and that discrepancy once
     * propagated into a published cycle count. Print what the silicon is
     * actually running at so the capture log is self-documenting.
     */
    uint32_t _clk = clock_get_hz(clk_sys);
    printf("# CPU: %lu Hz measured (clk_sys)\n", (unsigned long)_clk);
    if (_clk != 125000000u) {
        printf("# WARNING: clk_sys is not the expected 125000000 Hz — "
               "cycle conversions in the analysis scripts assume 125 MHz\n");
    }

    /*
     * Board identity. The 64-bit flash JEDEC unique ID is distinct per
     * board, so it is what distinguishes unit 1 from unit 2 in the
     * two-unit comparison. Recorded here rather than typed in by hand:
     * a mislabelled capture would silently invalidate the whole
     * inter-unit analysis.
     */
    pico_unique_board_id_t _bid;
    pico_get_unique_board_id(&_bid);
    printf("# Board unique ID: ");
    for (int _i = 0; _i < PICO_UNIQUE_BOARD_ID_SIZE_BYTES; _i++)
        printf("%02X", _bid.id[_i]);
    printf("\n");

    printf("# RAM: 264 KB, Flash: 2 MB\n");
    printf("# Build: %s %s | gcc %s\n", __DATE__, __TIME__, __VERSION__);
    printf("# Runs per operation: %d (signing: %d)\n",
           NUM_RUNS, NUM_RUNS_DSA_SIGN);
    printf("#\n");
}

#endif /* BENCH_HARNESS_H */
