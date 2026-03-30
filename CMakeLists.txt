cmake_minimum_required(VERSION 3.13)

# Pull in Pico SDK (must be before project())
include($ENV{PICO_SDK_PATH}/external/pico_sdk_import.cmake)

project(pqc_cortex_m0_benchmark C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

# Initialize the Pico SDK
pico_sdk_init()

# ============================================================
# PQClean paths — reference C implementations (not liboqs)
# Per review recommendation: PQClean is portable, well-tested,
# and forms the basis of pqm4's implementations.
# ============================================================
set(PQCLEAN_DIR ${CMAKE_CURRENT_SOURCE_DIR}/pqclean)
set(PQCLEAN_COMMON ${PQCLEAN_DIR}/common)

# ============================================================
# PQClean common library (fips202/keccak, sha2, sp800-185)
# Note: we use our own randombytes_pico.c instead of PQClean's
# randombytes.c (which targets desktop OSes)
# ============================================================
add_library(pqclean_common STATIC
    ${PQCLEAN_COMMON}/fips202.c
    ${PQCLEAN_COMMON}/sha2.c
    ${PQCLEAN_COMMON}/sp800-185.c
    src/randombytes_pico.c
)
target_include_directories(pqclean_common PUBLIC ${PQCLEAN_COMMON})
target_link_libraries(pqclean_common pico_stdlib hardware_structs)

# ============================================================
# ML-KEM-512 (PQClean clean reference C)
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
# ML-KEM-768 (PQClean clean reference C)
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
# ML-KEM-1024 (PQClean clean reference C)
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
# ML-DSA-44 (PQClean clean reference C)
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
# ML-DSA-65 (PQClean clean reference C)
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
# ML-DSA-87 (PQClean clean reference C)
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
# Custom linker script: stack in main RAM (not SCRATCH_Y)
# Needed for PQC ops that need >4KB stack
# ============================================================
set(CUSTOM_LINKER_SCRIPT ${CMAKE_CURRENT_SOURCE_DIR}/memmap_custom.ld)

# ============================================================
# Blink test — verify toolchain works (uses default linker)
# ============================================================
add_executable(blink src/blink.c)
target_link_libraries(blink pico_stdlib)
pico_add_extra_outputs(blink)
pico_enable_stdio_usb(blink 1)
pico_enable_stdio_uart(blink 0)

# ============================================================
# Benchmark: Classical (RSA-2048, ECDSA P-256, ECDH P-256)
# Uses pico-sdk's pico_mbedtls with our custom mbedtls_config.h
# ============================================================
add_executable(bench_classical src/bench_classical.c)
target_include_directories(bench_classical PRIVATE src)
target_link_libraries(bench_classical
    pico_stdlib
    pico_mbedtls
)
pico_add_extra_outputs(bench_classical)
pico_enable_stdio_usb(bench_classical 1)
pico_enable_stdio_uart(bench_classical 0)
target_compile_definitions(bench_classical PRIVATE PICO_STACK_SIZE=0x10000)
pico_set_linker_script(bench_classical ${CUSTOM_LINKER_SCRIPT})

# ============================================================
# Benchmark: ML-KEM (all security levels) — PQClean
# ============================================================
add_executable(bench_mlkem src/bench_mlkem.c)
target_include_directories(bench_mlkem PRIVATE src)
target_link_libraries(bench_mlkem
    pico_stdlib
    mlkem512 mlkem768 mlkem1024
    pqclean_common
)
pico_add_extra_outputs(bench_mlkem)
pico_enable_stdio_usb(bench_mlkem 1)
pico_enable_stdio_uart(bench_mlkem 0)
target_compile_definitions(bench_mlkem PRIVATE PICO_STACK_SIZE=0x10000)
pico_set_linker_script(bench_mlkem ${CUSTOM_LINKER_SCRIPT})

# ============================================================
# Benchmark: ML-DSA (all security levels) — PQClean
# ============================================================
add_executable(bench_mldsa src/bench_mldsa.c)
target_include_directories(bench_mldsa PRIVATE src)
target_link_libraries(bench_mldsa
    pico_stdlib
    mldsa44 mldsa65 mldsa87
    pqclean_common
)
pico_add_extra_outputs(bench_mldsa)
pico_enable_stdio_usb(bench_mldsa 1)
pico_enable_stdio_uart(bench_mldsa 0)
target_compile_definitions(bench_mldsa PRIVATE PICO_STACK_SIZE=0x30000)
target_compile_options(bench_mldsa PRIVATE -fstack-usage)
pico_set_linker_script(bench_mldsa ${CUSTOM_LINKER_SCRIPT})
