cmake_minimum_required(VERSION 3.10)
project(pqc_local_bench C)
set(CMAKE_C_STANDARD 99)

# Compatibility shim for old MinGW missing crtdefs.h
include_directories(BEFORE ${CMAKE_CURRENT_SOURCE_DIR}/compat)

# PQClean paths
set(PQCLEAN_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../pqclean)
set(PQCLEAN_COMMON ${PQCLEAN_DIR}/common)

# ============================================================
# Common library (fips202/keccak, randombytes, sha2)
# ============================================================
add_library(pqclean_common STATIC
    ${PQCLEAN_COMMON}/fips202.c
    ${PQCLEAN_COMMON}/sha2.c
    ${PQCLEAN_COMMON}/sp800-185.c
    ${PQCLEAN_COMMON}/randombytes.c
)
target_include_directories(pqclean_common PUBLIC ${PQCLEAN_COMMON})
# Windows needs advapi32 for CryptGenRandom
if(WIN32)
    target_link_libraries(pqclean_common advapi32)
endif()

# ============================================================
# ML-KEM-512 (clean reference C)
# ============================================================
set(MLKEM512_DIR ${PQCLEAN_DIR}/crypto_kem/ml-kem-512/clean)
add_library(mlkem512 STATIC
    ${MLKEM512_DIR}/cbd.c
    ${MLKEM512_DIR}/indcpa.c
    ${MLKEM512_DIR}/kem.c
    ${MLKEM512_DIR}/ntt.c
    ${MLKEM512_DIR}/poly.c
    ${MLKEM512_DIR}/polyvec.c
    ${MLKEM512_DIR}/reduce.c
    ${MLKEM512_DIR}/symmetric-shake.c
    ${MLKEM512_DIR}/verify.c
)
target_include_directories(mlkem512 PUBLIC ${MLKEM512_DIR} ${PQCLEAN_COMMON})

# ============================================================
# ML-KEM-768 (clean reference C)
# ============================================================
set(MLKEM768_DIR ${PQCLEAN_DIR}/crypto_kem/ml-kem-768/clean)
add_library(mlkem768 STATIC
    ${MLKEM768_DIR}/cbd.c
    ${MLKEM768_DIR}/indcpa.c
    ${MLKEM768_DIR}/kem.c
    ${MLKEM768_DIR}/ntt.c
    ${MLKEM768_DIR}/poly.c
    ${MLKEM768_DIR}/polyvec.c
    ${MLKEM768_DIR}/reduce.c
    ${MLKEM768_DIR}/symmetric-shake.c
    ${MLKEM768_DIR}/verify.c
)
target_include_directories(mlkem768 PUBLIC ${MLKEM768_DIR} ${PQCLEAN_COMMON})

# ============================================================
# ML-KEM-1024 (clean reference C)
# ============================================================
set(MLKEM1024_DIR ${PQCLEAN_DIR}/crypto_kem/ml-kem-1024/clean)
add_library(mlkem1024 STATIC
    ${MLKEM1024_DIR}/cbd.c
    ${MLKEM1024_DIR}/indcpa.c
    ${MLKEM1024_DIR}/kem.c
    ${MLKEM1024_DIR}/ntt.c
    ${MLKEM1024_DIR}/poly.c
    ${MLKEM1024_DIR}/polyvec.c
    ${MLKEM1024_DIR}/reduce.c
    ${MLKEM1024_DIR}/symmetric-shake.c
    ${MLKEM1024_DIR}/verify.c
)
target_include_directories(mlkem1024 PUBLIC ${MLKEM1024_DIR} ${PQCLEAN_COMMON})

# ============================================================
# ML-DSA-44 (clean reference C)
# ============================================================
set(MLDSA44_DIR ${PQCLEAN_DIR}/crypto_sign/ml-dsa-44/clean)
add_library(mldsa44 STATIC
    ${MLDSA44_DIR}/ntt.c
    ${MLDSA44_DIR}/packing.c
    ${MLDSA44_DIR}/poly.c
    ${MLDSA44_DIR}/polyvec.c
    ${MLDSA44_DIR}/reduce.c
    ${MLDSA44_DIR}/rounding.c
    ${MLDSA44_DIR}/sign.c
    ${MLDSA44_DIR}/symmetric-shake.c
)
target_include_directories(mldsa44 PUBLIC ${MLDSA44_DIR} ${PQCLEAN_COMMON})

# ============================================================
# ML-DSA-65 (clean reference C)
# ============================================================
set(MLDSA65_DIR ${PQCLEAN_DIR}/crypto_sign/ml-dsa-65/clean)
add_library(mldsa65 STATIC
    ${MLDSA65_DIR}/ntt.c
    ${MLDSA65_DIR}/packing.c
    ${MLDSA65_DIR}/poly.c
    ${MLDSA65_DIR}/polyvec.c
    ${MLDSA65_DIR}/reduce.c
    ${MLDSA65_DIR}/rounding.c
    ${MLDSA65_DIR}/sign.c
    ${MLDSA65_DIR}/symmetric-shake.c
)
target_include_directories(mldsa65 PUBLIC ${MLDSA65_DIR} ${PQCLEAN_COMMON})

# ============================================================
# ML-DSA-87 (clean reference C)
# ============================================================
set(MLDSA87_DIR ${PQCLEAN_DIR}/crypto_sign/ml-dsa-87/clean)
add_library(mldsa87 STATIC
    ${MLDSA87_DIR}/ntt.c
    ${MLDSA87_DIR}/packing.c
    ${MLDSA87_DIR}/poly.c
    ${MLDSA87_DIR}/polyvec.c
    ${MLDSA87_DIR}/reduce.c
    ${MLDSA87_DIR}/rounding.c
    ${MLDSA87_DIR}/sign.c
    ${MLDSA87_DIR}/symmetric-shake.c
)
target_include_directories(mldsa87 PUBLIC ${MLDSA87_DIR} ${PQCLEAN_COMMON})

# ============================================================
# Benchmark: ML-KEM (local PC)
# ============================================================
add_executable(bench_mlkem_local bench_mlkem_local.c)
target_include_directories(bench_mlkem_local PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${PQCLEAN_DIR}/crypto_kem
)
target_link_libraries(bench_mlkem_local mlkem512 mlkem768 mlkem1024 pqclean_common)

# ============================================================
# Benchmark: ML-DSA (local PC)
# ============================================================
add_executable(bench_mldsa_local bench_mldsa_local.c)
target_include_directories(bench_mldsa_local PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${PQCLEAN_DIR}/crypto_sign
)
target_link_libraries(bench_mldsa_local mldsa44 mldsa65 mldsa87 pqclean_common)
