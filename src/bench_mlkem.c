/*
 * bench_mlkem.c — ML-KEM (FIPS 203) benchmark on RP2040
 *
 * Uses PQClean reference C implementations (not liboqs).
 * Tests all three security levels: ML-KEM-512, ML-KEM-768, ML-KEM-1024
 * Operations: keygen, encaps, decaps (30 runs each)
 */

#include "bench_harness.h"

/* PQClean ML-KEM APIs (copied from pqclean crypto_kem clean api.h) */
#include "api_mlkem512.h"
#include "api_mlkem768.h"
#include "api_mlkem1024.h"

/* ================================================================
 * ML-KEM-512
 * ================================================================ */
static void bench_mlkem512(void) {
    uint8_t pk[PQCLEAN_MLKEM512_CLEAN_CRYPTO_PUBLICKEYBYTES];
    uint8_t sk[PQCLEAN_MLKEM512_CLEAN_CRYPTO_SECRETKEYBYTES];
    uint8_t ct[PQCLEAN_MLKEM512_CLEAN_CRYPTO_CIPHERTEXTBYTES];
    uint8_t ss_enc[PQCLEAN_MLKEM512_CLEAN_CRYPTO_BYTES];
    uint8_t ss_dec[PQCLEAN_MLKEM512_CLEAN_CRYPTO_BYTES];
    int rc;

    printf("# --- ML-KEM-512 (FIPS 203) ---\n");
    printf("# PK=%d SK=%d CT=%d SS=%d bytes\n",
           PQCLEAN_MLKEM512_CLEAN_CRYPTO_PUBLICKEYBYTES,
           PQCLEAN_MLKEM512_CLEAN_CRYPTO_SECRETKEYBYTES,
           PQCLEAN_MLKEM512_CLEAN_CRYPTO_CIPHERTEXTBYTES,
           PQCLEAN_MLKEM512_CLEAN_CRYPTO_BYTES);

    BENCH_RUN("ML-KEM", "keygen", 512, {
        rc = PQCLEAN_MLKEM512_CLEAN_crypto_kem_keypair(pk, sk);
        if (rc != 0) printf("# ERROR: keygen failed rc=%d\n", rc);
    });

    PQCLEAN_MLKEM512_CLEAN_crypto_kem_keypair(pk, sk);

    BENCH_RUN("ML-KEM", "encaps", 512, {
        rc = PQCLEAN_MLKEM512_CLEAN_crypto_kem_enc(ct, ss_enc, pk);
        if (rc != 0) printf("# ERROR: encaps failed rc=%d\n", rc);
    });

    PQCLEAN_MLKEM512_CLEAN_crypto_kem_enc(ct, ss_enc, pk);

    BENCH_RUN("ML-KEM", "decaps", 512, {
        rc = PQCLEAN_MLKEM512_CLEAN_crypto_kem_dec(ss_dec, ct, sk);
        if (rc != 0) printf("# ERROR: decaps failed rc=%d\n", rc);
    });

    if (memcmp(ss_enc, ss_dec, PQCLEAN_MLKEM512_CLEAN_CRYPTO_BYTES) == 0) {
        printf("# CORRECTNESS: ML-KEM-512 shared secrets MATCH\n");
    } else {
        printf("# CORRECTNESS ERROR: ML-KEM-512 shared secrets DO NOT MATCH!\n");
    }

    /* Stack measurements (one run each) */
    BENCH_STACK("ML-KEM", "keygen", 512, {
        PQCLEAN_MLKEM512_CLEAN_crypto_kem_keypair(pk, sk);
    });
    PQCLEAN_MLKEM512_CLEAN_crypto_kem_keypair(pk, sk);
    BENCH_STACK("ML-KEM", "encaps", 512, {
        PQCLEAN_MLKEM512_CLEAN_crypto_kem_enc(ct, ss_enc, pk);
    });
    PQCLEAN_MLKEM512_CLEAN_crypto_kem_enc(ct, ss_enc, pk);
    BENCH_STACK("ML-KEM", "decaps", 512, {
        PQCLEAN_MLKEM512_CLEAN_crypto_kem_dec(ss_dec, ct, sk);
    });
}

/* ================================================================
 * ML-KEM-768
 * ================================================================ */
static void bench_mlkem768(void) {
    uint8_t pk[PQCLEAN_MLKEM768_CLEAN_CRYPTO_PUBLICKEYBYTES];
    uint8_t sk[PQCLEAN_MLKEM768_CLEAN_CRYPTO_SECRETKEYBYTES];
    uint8_t ct[PQCLEAN_MLKEM768_CLEAN_CRYPTO_CIPHERTEXTBYTES];
    uint8_t ss_enc[PQCLEAN_MLKEM768_CLEAN_CRYPTO_BYTES];
    uint8_t ss_dec[PQCLEAN_MLKEM768_CLEAN_CRYPTO_BYTES];
    int rc;

    printf("# --- ML-KEM-768 (FIPS 203) ---\n");
    printf("# PK=%d SK=%d CT=%d SS=%d bytes\n",
           PQCLEAN_MLKEM768_CLEAN_CRYPTO_PUBLICKEYBYTES,
           PQCLEAN_MLKEM768_CLEAN_CRYPTO_SECRETKEYBYTES,
           PQCLEAN_MLKEM768_CLEAN_CRYPTO_CIPHERTEXTBYTES,
           PQCLEAN_MLKEM768_CLEAN_CRYPTO_BYTES);

    BENCH_RUN("ML-KEM", "keygen", 768, {
        rc = PQCLEAN_MLKEM768_CLEAN_crypto_kem_keypair(pk, sk);
        if (rc != 0) printf("# ERROR: keygen failed rc=%d\n", rc);
    });

    PQCLEAN_MLKEM768_CLEAN_crypto_kem_keypair(pk, sk);

    BENCH_RUN("ML-KEM", "encaps", 768, {
        rc = PQCLEAN_MLKEM768_CLEAN_crypto_kem_enc(ct, ss_enc, pk);
        if (rc != 0) printf("# ERROR: encaps failed rc=%d\n", rc);
    });

    PQCLEAN_MLKEM768_CLEAN_crypto_kem_enc(ct, ss_enc, pk);

    BENCH_RUN("ML-KEM", "decaps", 768, {
        rc = PQCLEAN_MLKEM768_CLEAN_crypto_kem_dec(ss_dec, ct, sk);
        if (rc != 0) printf("# ERROR: decaps failed rc=%d\n", rc);
    });

    if (memcmp(ss_enc, ss_dec, PQCLEAN_MLKEM768_CLEAN_CRYPTO_BYTES) == 0) {
        printf("# CORRECTNESS: ML-KEM-768 shared secrets MATCH\n");
    } else {
        printf("# CORRECTNESS ERROR: ML-KEM-768 shared secrets DO NOT MATCH!\n");
    }

    BENCH_STACK("ML-KEM", "keygen", 768, {
        PQCLEAN_MLKEM768_CLEAN_crypto_kem_keypair(pk, sk);
    });
    PQCLEAN_MLKEM768_CLEAN_crypto_kem_keypair(pk, sk);
    BENCH_STACK("ML-KEM", "encaps", 768, {
        PQCLEAN_MLKEM768_CLEAN_crypto_kem_enc(ct, ss_enc, pk);
    });
    PQCLEAN_MLKEM768_CLEAN_crypto_kem_enc(ct, ss_enc, pk);
    BENCH_STACK("ML-KEM", "decaps", 768, {
        PQCLEAN_MLKEM768_CLEAN_crypto_kem_dec(ss_dec, ct, sk);
    });
}

/* ================================================================
 * ML-KEM-1024
 * ================================================================ */
static void bench_mlkem1024(void) {
    uint8_t pk[PQCLEAN_MLKEM1024_CLEAN_CRYPTO_PUBLICKEYBYTES];
    uint8_t sk[PQCLEAN_MLKEM1024_CLEAN_CRYPTO_SECRETKEYBYTES];
    uint8_t ct[PQCLEAN_MLKEM1024_CLEAN_CRYPTO_CIPHERTEXTBYTES];
    uint8_t ss_enc[PQCLEAN_MLKEM1024_CLEAN_CRYPTO_BYTES];
    uint8_t ss_dec[PQCLEAN_MLKEM1024_CLEAN_CRYPTO_BYTES];
    int rc;

    printf("# --- ML-KEM-1024 (FIPS 203) ---\n");
    printf("# PK=%d SK=%d CT=%d SS=%d bytes\n",
           PQCLEAN_MLKEM1024_CLEAN_CRYPTO_PUBLICKEYBYTES,
           PQCLEAN_MLKEM1024_CLEAN_CRYPTO_SECRETKEYBYTES,
           PQCLEAN_MLKEM1024_CLEAN_CRYPTO_CIPHERTEXTBYTES,
           PQCLEAN_MLKEM1024_CLEAN_CRYPTO_BYTES);

    BENCH_RUN("ML-KEM", "keygen", 1024, {
        rc = PQCLEAN_MLKEM1024_CLEAN_crypto_kem_keypair(pk, sk);
        if (rc != 0) printf("# ERROR: keygen failed rc=%d\n", rc);
    });

    PQCLEAN_MLKEM1024_CLEAN_crypto_kem_keypair(pk, sk);

    BENCH_RUN("ML-KEM", "encaps", 1024, {
        rc = PQCLEAN_MLKEM1024_CLEAN_crypto_kem_enc(ct, ss_enc, pk);
        if (rc != 0) printf("# ERROR: encaps failed rc=%d\n", rc);
    });

    PQCLEAN_MLKEM1024_CLEAN_crypto_kem_enc(ct, ss_enc, pk);

    BENCH_RUN("ML-KEM", "decaps", 1024, {
        rc = PQCLEAN_MLKEM1024_CLEAN_crypto_kem_dec(ss_dec, ct, sk);
        if (rc != 0) printf("# ERROR: decaps failed rc=%d\n", rc);
    });

    if (memcmp(ss_enc, ss_dec, PQCLEAN_MLKEM1024_CLEAN_CRYPTO_BYTES) == 0) {
        printf("# CORRECTNESS: ML-KEM-1024 shared secrets MATCH\n");
    } else {
        printf("# CORRECTNESS ERROR: ML-KEM-1024 shared secrets DO NOT MATCH!\n");
    }

    BENCH_STACK("ML-KEM", "keygen", 1024, {
        PQCLEAN_MLKEM1024_CLEAN_crypto_kem_keypair(pk, sk);
    });
    PQCLEAN_MLKEM1024_CLEAN_crypto_kem_keypair(pk, sk);
    BENCH_STACK("ML-KEM", "encaps", 1024, {
        PQCLEAN_MLKEM1024_CLEAN_crypto_kem_enc(ct, ss_enc, pk);
    });
    PQCLEAN_MLKEM1024_CLEAN_crypto_kem_enc(ct, ss_enc, pk);
    BENCH_STACK("ML-KEM", "decaps", 1024, {
        PQCLEAN_MLKEM1024_CLEAN_crypto_kem_dec(ss_dec, ct, sk);
    });
}

/* ================================================================ */
int main(void) {
    bench_init();
    bench_csv_header();

    bench_mlkem512();
    bench_mlkem768();
    bench_mlkem1024();

    printf("# === ML-KEM benchmarks complete ===\n");

    while (true) {
        sleep_ms(10000);
    }
    return 0;
}
