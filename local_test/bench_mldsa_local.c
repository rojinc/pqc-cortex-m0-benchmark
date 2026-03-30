/*
 * bench_mldsa_local.c — ML-DSA benchmark using PQClean (local PC)
 *
 * Tests all three security levels: ML-DSA-44, ML-DSA-65, ML-DSA-87
 * Operations: keygen (30 runs), sign (100 runs for variance), verify (30 runs)
 * Signing uses 100 runs to capture rejection sampling variance.
 */

#include "bench_harness_local.h"

/* PQClean ML-DSA APIs */
#include "ml-dsa-44/clean/api.h"
#include "ml-dsa-65/clean/api.h"
#include "ml-dsa-87/clean/api.h"

static const uint8_t test_message[] =
    "This is a test message for ML-DSA benchmarking on ARM Cortex-M0+. "
    "The Raspberry Pi Pico RP2040 has 264KB RAM and runs at 133MHz.";
static const size_t test_message_len = sizeof(test_message) - 1;

/* ================================================================
 * ML-DSA-44
 * ================================================================ */
static void bench_mldsa44(void) {
    uint8_t pk[PQCLEAN_MLDSA44_CLEAN_CRYPTO_PUBLICKEYBYTES];
    uint8_t sk[PQCLEAN_MLDSA44_CLEAN_CRYPTO_SECRETKEYBYTES];
    uint8_t sig[PQCLEAN_MLDSA44_CLEAN_CRYPTO_BYTES];
    size_t sig_len;
    int rc;

    printf("# --- ML-DSA-44 ---\n");
    printf("# PK=%d SK=%d SIG=%d bytes\n",
           PQCLEAN_MLDSA44_CLEAN_CRYPTO_PUBLICKEYBYTES,
           PQCLEAN_MLDSA44_CLEAN_CRYPTO_SECRETKEYBYTES,
           PQCLEAN_MLDSA44_CLEAN_CRYPTO_BYTES);

    BENCH_RUN("ML-DSA", "keygen", 44, NUM_RUNS, {
        rc = PQCLEAN_MLDSA44_CLEAN_crypto_sign_keypair(pk, sk);
        if (rc != 0) printf("# ERROR: keygen failed rc=%d\n", rc);
    });

    PQCLEAN_MLDSA44_CLEAN_crypto_sign_keypair(pk, sk);

    BENCH_RUN("ML-DSA", "sign", 44, NUM_RUNS_DSA_SIGN, {
        rc = PQCLEAN_MLDSA44_CLEAN_crypto_sign_signature(sig, &sig_len,
                test_message, test_message_len, sk);
        if (rc != 0) printf("# ERROR: sign failed rc=%d\n", rc);
    });

    PQCLEAN_MLDSA44_CLEAN_crypto_sign_signature(sig, &sig_len,
            test_message, test_message_len, sk);

    BENCH_RUN("ML-DSA", "verify", 44, NUM_RUNS, {
        rc = PQCLEAN_MLDSA44_CLEAN_crypto_sign_verify(sig, sig_len,
                test_message, test_message_len, pk);
        if (rc != 0) printf("# ERROR: verify failed rc=%d\n", rc);
    });

    rc = PQCLEAN_MLDSA44_CLEAN_crypto_sign_verify(sig, sig_len,
            test_message, test_message_len, pk);
    if (rc == 0) {
        printf("# CORRECTNESS: ML-DSA-44 signature verifies OK\n");
    } else {
        printf("# CORRECTNESS ERROR: ML-DSA-44 signature INVALID!\n");
    }
}

/* ================================================================
 * ML-DSA-65
 * ================================================================ */
static void bench_mldsa65(void) {
    uint8_t pk[PQCLEAN_MLDSA65_CLEAN_CRYPTO_PUBLICKEYBYTES];
    uint8_t sk[PQCLEAN_MLDSA65_CLEAN_CRYPTO_SECRETKEYBYTES];
    uint8_t sig[PQCLEAN_MLDSA65_CLEAN_CRYPTO_BYTES];
    size_t sig_len;
    int rc;

    printf("# --- ML-DSA-65 ---\n");
    printf("# PK=%d SK=%d SIG=%d bytes\n",
           PQCLEAN_MLDSA65_CLEAN_CRYPTO_PUBLICKEYBYTES,
           PQCLEAN_MLDSA65_CLEAN_CRYPTO_SECRETKEYBYTES,
           PQCLEAN_MLDSA65_CLEAN_CRYPTO_BYTES);

    BENCH_RUN("ML-DSA", "keygen", 65, NUM_RUNS, {
        rc = PQCLEAN_MLDSA65_CLEAN_crypto_sign_keypair(pk, sk);
        if (rc != 0) printf("# ERROR: keygen failed rc=%d\n", rc);
    });

    PQCLEAN_MLDSA65_CLEAN_crypto_sign_keypair(pk, sk);

    BENCH_RUN("ML-DSA", "sign", 65, NUM_RUNS_DSA_SIGN, {
        rc = PQCLEAN_MLDSA65_CLEAN_crypto_sign_signature(sig, &sig_len,
                test_message, test_message_len, sk);
        if (rc != 0) printf("# ERROR: sign failed rc=%d\n", rc);
    });

    PQCLEAN_MLDSA65_CLEAN_crypto_sign_signature(sig, &sig_len,
            test_message, test_message_len, sk);

    BENCH_RUN("ML-DSA", "verify", 65, NUM_RUNS, {
        rc = PQCLEAN_MLDSA65_CLEAN_crypto_sign_verify(sig, sig_len,
                test_message, test_message_len, pk);
        if (rc != 0) printf("# ERROR: verify failed rc=%d\n", rc);
    });

    rc = PQCLEAN_MLDSA65_CLEAN_crypto_sign_verify(sig, sig_len,
            test_message, test_message_len, pk);
    if (rc == 0) {
        printf("# CORRECTNESS: ML-DSA-65 signature verifies OK\n");
    } else {
        printf("# CORRECTNESS ERROR: ML-DSA-65 signature INVALID!\n");
    }
}

/* ================================================================
 * ML-DSA-87
 * ================================================================ */
static void bench_mldsa87(void) {
    uint8_t pk[PQCLEAN_MLDSA87_CLEAN_CRYPTO_PUBLICKEYBYTES];
    uint8_t sk[PQCLEAN_MLDSA87_CLEAN_CRYPTO_SECRETKEYBYTES];
    uint8_t sig[PQCLEAN_MLDSA87_CLEAN_CRYPTO_BYTES];
    size_t sig_len;
    int rc;

    printf("# --- ML-DSA-87 ---\n");
    printf("# PK=%d SK=%d SIG=%d bytes\n",
           PQCLEAN_MLDSA87_CLEAN_CRYPTO_PUBLICKEYBYTES,
           PQCLEAN_MLDSA87_CLEAN_CRYPTO_SECRETKEYBYTES,
           PQCLEAN_MLDSA87_CLEAN_CRYPTO_BYTES);

    BENCH_RUN("ML-DSA", "keygen", 87, NUM_RUNS, {
        rc = PQCLEAN_MLDSA87_CLEAN_crypto_sign_keypair(pk, sk);
        if (rc != 0) printf("# ERROR: keygen failed rc=%d\n", rc);
    });

    PQCLEAN_MLDSA87_CLEAN_crypto_sign_keypair(pk, sk);

    BENCH_RUN("ML-DSA", "sign", 87, NUM_RUNS_DSA_SIGN, {
        rc = PQCLEAN_MLDSA87_CLEAN_crypto_sign_signature(sig, &sig_len,
                test_message, test_message_len, sk);
        if (rc != 0) printf("# ERROR: sign failed rc=%d\n", rc);
    });

    PQCLEAN_MLDSA87_CLEAN_crypto_sign_signature(sig, &sig_len,
            test_message, test_message_len, sk);

    BENCH_RUN("ML-DSA", "verify", 87, NUM_RUNS, {
        rc = PQCLEAN_MLDSA87_CLEAN_crypto_sign_verify(sig, sig_len,
                test_message, test_message_len, pk);
        if (rc != 0) printf("# ERROR: verify failed rc=%d\n", rc);
    });

    rc = PQCLEAN_MLDSA87_CLEAN_crypto_sign_verify(sig, sig_len,
            test_message, test_message_len, pk);
    if (rc == 0) {
        printf("# CORRECTNESS: ML-DSA-87 signature verifies OK\n");
    } else {
        printf("# CORRECTNESS ERROR: ML-DSA-87 signature INVALID!\n");
    }
}

/* ================================================================ */
int main(void) {
    bench_init();
    bench_csv_header();

    bench_mldsa44();
    bench_mldsa65();
    bench_mldsa87();

    printf("# === ML-DSA benchmarks complete ===\n");
    return 0;
}
