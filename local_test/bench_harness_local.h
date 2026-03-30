/*
 * bench_harness_local.h — Local PC timing framework for PQC benchmarks
 *
 * Uses Windows QueryPerformanceCounter for microsecond-precision timing.
 * Runs each operation N times, computes mean/min/max/stddev,
 * and prints CSV output to stdout.
 *
 * CSV format: algorithm,operation,security_level,time_us,run_number
 */

#ifndef BENCH_HARNESS_LOCAL_H
#define BENCH_HARNESS_LOCAL_H

#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <windows.h>

#define NUM_RUNS          30
#define NUM_RUNS_DSA_SIGN 100

static LARGE_INTEGER _bench_freq;

static inline void bench_init(void) {
    QueryPerformanceFrequency(&_bench_freq);
    printf("# PQC Benchmark Suite (Local PC)\n");
    printf("# Using PQClean reference C implementations\n");
    printf("# Timer: QueryPerformanceCounter (%.0f ticks/sec)\n",
           (double)_bench_freq.QuadPart);
    printf("#\n");
}

static inline uint64_t bench_time_us(void) {
    LARGE_INTEGER t;
    QueryPerformanceCounter(&t);
    return (uint64_t)(t.QuadPart * 1000000ULL / _bench_freq.QuadPart);
}

static inline void bench_csv_header(void) {
    printf("algorithm,operation,security_level,time_us,run_number\n");
}

static inline void bench_csv_row(const char *algo, const char *op,
                                  int sec_level, uint64_t time_us, int run) {
    printf("%s,%s,%d,%llu,%d\n", algo, op, sec_level,
           (unsigned long long)time_us, run);
}

#define BENCH_RUN(algo, op, sec_level, num_runs, code_block)                  \
    do {                                                                       \
        uint64_t _times[num_runs];                                            \
        for (int _i = 0; _i < (num_runs); _i++) {                            \
            uint64_t _start = bench_time_us();                                \
            { code_block; }                                                   \
            uint64_t _end = bench_time_us();                                  \
            _times[_i] = _end - _start;                                       \
            bench_csv_row(algo, op, sec_level, _times[_i], _i + 1);           \
        }                                                                      \
        uint64_t _sum = 0;                                                    \
        uint64_t _min = UINT64_MAX, _max = 0;                                \
        for (int _i = 0; _i < (num_runs); _i++) {                            \
            _sum += _times[_i];                                                \
            if (_times[_i] < _min) _min = _times[_i];                         \
            if (_times[_i] > _max) _max = _times[_i];                         \
        }                                                                      \
        double _mean = (double)_sum / (num_runs);                             \
        double _var = 0;                                                       \
        for (int _i = 0; _i < (num_runs); _i++) {                            \
            double _d = (double)_times[_i] - _mean;                           \
            _var += _d * _d;                                                   \
        }                                                                      \
        double _stddev = sqrt(_var / (num_runs));                             \
        double _cv = (_mean > 0) ? (_stddev / _mean * 100.0) : 0;            \
        printf("# SUMMARY %s %s %d: mean=%.0f min=%llu max=%llu "            \
               "stddev=%.1f cv=%.2f%% (n=%d)\n",                              \
               algo, op, sec_level, _mean,                                     \
               (unsigned long long)_min, (unsigned long long)_max,             \
               _stddev, _cv, (num_runs));                                      \
    } while (0)

#endif /* BENCH_HARNESS_LOCAL_H */
