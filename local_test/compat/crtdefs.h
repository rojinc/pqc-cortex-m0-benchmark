/*
 * crtdefs.h compatibility shim for MinGW 6.3 (mingw32)
 * PQClean's randombytes.h includes <crtdefs.h> for size_t on Windows.
 * Older MinGW doesn't ship this header; stddef.h provides size_t.
 */
#ifndef _COMPAT_CRTDEFS_H
#define _COMPAT_CRTDEFS_H
#include <stddef.h>
#endif
