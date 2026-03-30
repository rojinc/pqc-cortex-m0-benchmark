/*
 * bench_classical.c — Classical crypto baseline benchmarks on RP2040
 *
 * Benchmarks RSA-2048 and ECDSA/ECDH P-256 using mbedTLS.
 * These provide the "before" comparison for PQC algorithms.
 *
 */

#include "bench_harness.h"

#include "mbedtls/rsa.h"
#include "mbedtls/pk.h"
#include "mbedtls/entropy.h"
#include "mbedtls/ctr_drbg.h"
#include "mbedtls/ecdsa.h"
#include "mbedtls/ecdh.h"
#include "mbedtls/ecp.h"
#include "mbedtls/md.h"
#include "mbedtls/error.h"

/* Simple deterministic RNG for benchmarking (seeded from hardware) */
static mbedtls_entropy_context entropy;
static mbedtls_ctr_drbg_context ctr_drbg;

static int rng_wrapper(void *ctx, unsigned char *buf, size_t len)
{
    return mbedtls_ctr_drbg_random(&ctr_drbg, buf, len);
}

static void init_rng(void)
{
    mbedtls_entropy_init(&entropy);
    mbedtls_ctr_drbg_init(&ctr_drbg);
    const char *pers = "pqc_bench";
    int ret = mbedtls_ctr_drbg_seed(&ctr_drbg, mbedtls_entropy_func,
                                    &entropy, (const unsigned char *)pers,
                                    strlen(pers));
    if (ret != 0)
    {
        printf("# ERROR: ctr_drbg_seed failed: %d\n", ret);
    }
}

/* ================================================================
 * RSA-2048 Benchmarks
 * ================================================================ */

static void bench_rsa2048(void)
{
    mbedtls_pk_context pk;
    int ret;

    printf("# --- RSA-2048 ---\n");

    /* Key generation — reduced to 5 runs because RSA keygen is ~50s per run on M0+ */
    uint32_t _rsa_kg_times[5];
    for (int _i = 0; _i < 5; _i++)
    {
        uint32_t _start = time_us_32();
        mbedtls_pk_init(&pk);
        mbedtls_pk_setup(&pk, mbedtls_pk_info_from_type(MBEDTLS_PK_RSA));
        ret = mbedtls_rsa_gen_key(mbedtls_pk_rsa(pk), rng_wrapper, NULL, 2048, 65537);
        uint32_t _end = time_us_32();
        _rsa_kg_times[_i] = _end - _start;
        if (ret != 0)
            printf("# ERROR: RSA keygen failed: %d\n", ret);
        bench_csv_row("RSA-2048", "keygen", 2048, _rsa_kg_times[_i], _i + 1);
        mbedtls_pk_free(&pk);
    }
    {
        uint64_t _sum = 0;
        uint32_t _min = UINT32_MAX, _max = 0;
        for (int _i = 0; _i < 5; _i++)
        {
            _sum += _rsa_kg_times[_i];
            if (_rsa_kg_times[_i] < _min)
                _min = _rsa_kg_times[_i];
            if (_rsa_kg_times[_i] > _max)
                _max = _rsa_kg_times[_i];
        }
        printf("# SUMMARY RSA-2048 keygen 2048: mean=%.0f min=%lu max=%lu (n=5)\n", (double)_sum / 5.0, (unsigned long)_min, (unsigned long)_max);
    }
    /* (original 30-run BENCH_RUN replaced with 5-run loop above) */

    /* For encrypt/decrypt and sign/verify, generate one key to reuse */
    mbedtls_pk_init(&pk);
    mbedtls_pk_setup(&pk, mbedtls_pk_info_from_type(MBEDTLS_PK_RSA));
    ret = mbedtls_rsa_gen_key(mbedtls_pk_rsa(pk), rng_wrapper, NULL, 2048, 65537);
    if (ret != 0)
    {
        printf("# ERROR: RSA keygen for enc/dec failed: %d\n", ret);
        return;
    }

    unsigned char plaintext[128];
    unsigned char ciphertext[256];
    unsigned char decrypted[256];
    size_t olen;

    memset(plaintext, 0x42, sizeof(plaintext));

    /* RSA Encrypt */
    BENCH_RUN("RSA-2048", "encrypt", 2048, {
        ret = mbedtls_rsa_pkcs1_encrypt(mbedtls_pk_rsa(pk), rng_wrapper, NULL,
                                        sizeof(plaintext), plaintext, ciphertext);
        if (ret != 0)
            printf("# ERROR: RSA encrypt: %d\n", ret);
    });

    /* RSA Decrypt */
    /* Encrypt once to get a valid ciphertext */
    mbedtls_rsa_pkcs1_encrypt(mbedtls_pk_rsa(pk), rng_wrapper, NULL,
                              sizeof(plaintext), plaintext, ciphertext);

    BENCH_RUN("RSA-2048", "decrypt", 2048, {
        ret = mbedtls_rsa_pkcs1_decrypt(mbedtls_pk_rsa(pk), rng_wrapper, NULL,
                                        &olen, ciphertext, decrypted,
                                        sizeof(decrypted));
        if (ret != 0)
            printf("# ERROR: RSA decrypt: %d\n", ret);
    });

    mbedtls_pk_free(&pk);
}

/* ================================================================
 * ECDSA P-256 Benchmarks
 * ================================================================ */

static void bench_ecdsa_p256(void)
{
    mbedtls_ecdsa_context ecdsa;
    mbedtls_mpi r, s;
    int ret;

    printf("# --- ECDSA P-256 ---\n");

    /* Key generation */
    BENCH_RUN("ECDSA-P256", "keygen", 256, {
        mbedtls_ecdsa_init(&ecdsa);
        ret = mbedtls_ecdsa_genkey(&ecdsa, MBEDTLS_ECP_DP_SECP256R1,
                                   rng_wrapper, NULL);
        if (ret != 0)
            printf("# ERROR: ECDSA keygen: %d\n", ret);
        mbedtls_ecdsa_free(&ecdsa);
    });

    /* Generate a persistent key for sign/verify */
    mbedtls_ecdsa_init(&ecdsa);
    mbedtls_ecdsa_genkey(&ecdsa, MBEDTLS_ECP_DP_SECP256R1, rng_wrapper, NULL);

    unsigned char hash[32];
    memset(hash, 0xAB, sizeof(hash));

    unsigned char sig[MBEDTLS_ECDSA_MAX_LEN];
    size_t sig_len;

    /* Sign */
    BENCH_RUN("ECDSA-P256", "sign", 256, {
        ret = mbedtls_ecdsa_write_signature(&ecdsa, MBEDTLS_MD_SHA256,
                                            hash, sizeof(hash),
                                            sig, sizeof(sig), &sig_len,
                                            rng_wrapper, NULL);
        if (ret != 0)
            printf("# ERROR: ECDSA sign: %d\n", ret);
    });

    /* Sign once for verify benchmark */
    mbedtls_ecdsa_write_signature(&ecdsa, MBEDTLS_MD_SHA256,
                                  hash, sizeof(hash),
                                  sig, sizeof(sig), &sig_len,
                                  rng_wrapper, NULL);

    /* Verify */
    BENCH_RUN("ECDSA-P256", "verify", 256, {
        ret = mbedtls_ecdsa_read_signature(&ecdsa, hash, sizeof(hash),
                                           sig, sig_len);
        if (ret != 0)
            printf("# ERROR: ECDSA verify: %d\n", ret);
    });

    mbedtls_ecdsa_free(&ecdsa);
}

/* ================================================================
 * ECDH P-256 Benchmarks
 * ================================================================ */

static void do_ecdh_key_agreement(void)
{
    mbedtls_ecdh_context ecdh_a;
    mbedtls_ecdh_context ecdh_b;
    mbedtls_ecdh_init(&ecdh_a);
    mbedtls_ecdh_init(&ecdh_b);

    mbedtls_ecdh_setup(&ecdh_a, MBEDTLS_ECP_DP_SECP256R1);
    mbedtls_ecdh_setup(&ecdh_b, MBEDTLS_ECP_DP_SECP256R1);

    unsigned char buf_a[100];
    unsigned char buf_b[100];
    unsigned char shared_a[32];
    unsigned char shared_b[32];
    size_t olen_a;
    size_t olen_b;
    size_t shared_len_a;
    size_t shared_len_b;

    mbedtls_ecdh_make_params(&ecdh_a, &olen_a, buf_a, sizeof(buf_a),
                             rng_wrapper, NULL);
    const unsigned char *p = buf_a;
    mbedtls_ecdh_read_params(&ecdh_b, &p, p + olen_a);
    mbedtls_ecdh_make_public(&ecdh_b, &olen_b, buf_b, sizeof(buf_b),
                             rng_wrapper, NULL);
    mbedtls_ecdh_read_public(&ecdh_a, buf_b, olen_b);

    mbedtls_ecdh_calc_secret(&ecdh_a, &shared_len_a, shared_a,
                             sizeof(shared_a), rng_wrapper, NULL);
    mbedtls_ecdh_calc_secret(&ecdh_b, &shared_len_b, shared_b,
                             sizeof(shared_b), rng_wrapper, NULL);

    mbedtls_ecdh_free(&ecdh_a);
    mbedtls_ecdh_free(&ecdh_b);
}

static void bench_ecdh_p256(void)
{
    printf("# --- ECDH P-256 ---\n");

    BENCH_RUN("ECDH-P256", "key_agreement", 256, {
        do_ecdh_key_agreement();
    });
}

/* ================================================================
 * Main
 * ================================================================ */

int main(void)
{
    bench_init();
    init_rng();

    bench_csv_header();

    bench_rsa2048();
    bench_ecdsa_p256();
    bench_ecdh_p256();

    printf("# === Classical baseline benchmarks complete ===\n");
    printf("# Save this output as results/raw/classical_baseline.csv\n");

    while (true)
    {
        sleep_ms(10000);
    }
    return 0;
}
