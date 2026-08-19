/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Purpose-written LD_PRELOAD allocation interposer for the runner capability
 * probe. Wraps malloc/free/calloc/realloc/posix_memalign/aligned_alloc with
 * relaxed atomic call and byte counters and dumps them at process exit.
 *
 * This object counts allocations for the whole process, never for any one
 * subsystem inside it, and is built only from this first-party source
 * committed to this repository by scripts/build_malloc_interposer.sh --
 * never from workflow input, pull-request content, or a downloaded
 * artifact.
 * ----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to
 * the license terms in the LICENSE.txt file found in the top-level directory
 * of this distribution and at:
 *    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
 * No part of the rogue software platform, including this file, may be
 * copied, modified, propagated, or distributed except according to the terms
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
 **/

#define _GNU_SOURCE

#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdatomic.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* Counters. Prefixed rogue_probe_ so they cannot collide with library or
 * application symbols in the address space this object is preloaded into. */
static atomic_ullong rogue_probe_malloc_calls = 0;
static atomic_ullong rogue_probe_free_calls = 0;
static atomic_ullong rogue_probe_calloc_calls = 0;
static atomic_ullong rogue_probe_realloc_calls = 0;
static atomic_ullong rogue_probe_aligned_calls = 0;
static atomic_ullong rogue_probe_bytes_requested = 0;

/* Real symbol pointers, resolved lazily on first use via dlsym(RTLD_NEXT).
 * Left NULL until resolve_real_symbols() runs the first time any wrapper
 * below is entered. */
typedef void *(*malloc_fn_t)(size_t);
typedef void (*free_fn_t)(void *);
typedef void *(*calloc_fn_t)(size_t, size_t);
typedef void *(*realloc_fn_t)(void *, size_t);
typedef int (*posix_memalign_fn_t)(void **, size_t, size_t);
typedef void *(*aligned_alloc_fn_t)(size_t, size_t);

static malloc_fn_t real_malloc = NULL;
static free_fn_t real_free = NULL;
static calloc_fn_t real_calloc = NULL;
static realloc_fn_t real_realloc = NULL;
static posix_memalign_fn_t real_posix_memalign = NULL;
static aligned_alloc_fn_t real_aligned_alloc = NULL;

/*
 * Recursion hazard, and the reason this file cannot be simplified: on glibc,
 * dlsym(RTLD_NEXT, ...) itself allocates memory as part of resolving a
 * symbol the first time it is called from a given library. Since dlsym is
 * called from inside this file's own calloc()/malloc() wrappers (to resolve
 * the *real* calloc/malloc), that inner allocation re-enters this file's own
 * wrapper before real_calloc/real_malloc have been assigned -- which would
 * call dlsym again, forever, until the stack overflows.
 *
 * The fix is a small static bootstrap buffer: while `in_dlsym` is set (i.e.
 * we are already inside resolve_real_symbols()), any wrapper whose real_*
 * pointer is still NULL serves the request from this buffer instead of
 * recursing into resolution again. Frees against a bootstrap address are
 * recognized by pointer range and silently ignored, since the bootstrap
 * pool is never individually freed -- it is reclaimed as a whole when the
 * process exits. Do not remove this: a later reader who "simplifies" this
 * away by always calling resolve_real_symbols() unconditionally will
 * reintroduce the hang.
 */
#define BOOTSTRAP_POOL_BYTES ((size_t)(1 << 16))
static unsigned char bootstrap_pool[BOOTSTRAP_POOL_BYTES];
static size_t bootstrap_offset = 0;
static int in_dlsym = 0;

static void *bootstrap_alloc(size_t size) {
    size_t aligned = (size + 15UL) & ~(size_t)15UL;
    if (aligned == 0) {
        aligned = 16UL;
    }
    if (bootstrap_offset + aligned > BOOTSTRAP_POOL_BYTES) {
        return NULL;
    }
    void *ptr = &bootstrap_pool[bootstrap_offset];
    bootstrap_offset += aligned;
    return ptr;
}

static int is_bootstrap_ptr(void *ptr) {
    unsigned char *candidate = (unsigned char *)ptr;
    return ptr != NULL && candidate >= bootstrap_pool && candidate < bootstrap_pool + BOOTSTRAP_POOL_BYTES;
}

static void resolve_real_symbols(void) {
    if (real_malloc != NULL) {
        return;
    }
    in_dlsym = 1;
    real_malloc = (malloc_fn_t)dlsym(RTLD_NEXT, "malloc");
    real_free = (free_fn_t)dlsym(RTLD_NEXT, "free");
    real_calloc = (calloc_fn_t)dlsym(RTLD_NEXT, "calloc");
    real_realloc = (realloc_fn_t)dlsym(RTLD_NEXT, "realloc");
    real_posix_memalign = (posix_memalign_fn_t)dlsym(RTLD_NEXT, "posix_memalign");
    real_aligned_alloc = (aligned_alloc_fn_t)dlsym(RTLD_NEXT, "aligned_alloc");
    in_dlsym = 0;
}

void *malloc(size_t size) {
    if (real_malloc == NULL) {
        if (in_dlsym) {
            return bootstrap_alloc(size);
        }
        resolve_real_symbols();
    }
    atomic_fetch_add(&rogue_probe_malloc_calls, 1ULL);
    atomic_fetch_add(&rogue_probe_bytes_requested, (unsigned long long)size);
    return real_malloc(size);
}

void free(void *ptr) {
    if (ptr == NULL) {
        return;
    }
    if (is_bootstrap_ptr(ptr)) {
        /* Bootstrap allocations are never individually freed; ignore the
         * request rather than pass a bootstrap-pool address to real_free. */
        return;
    }
    if (real_free == NULL) {
        if (in_dlsym) {
            /* Nothing frees during symbol resolution in practice, but never
             * call through an unresolved real_free. */
            return;
        }
        resolve_real_symbols();
    }
    atomic_fetch_add(&rogue_probe_free_calls, 1ULL);
    real_free(ptr);
}

void *calloc(size_t nmemb, size_t size) {
    if (real_calloc == NULL) {
        if (in_dlsym) {
            return bootstrap_alloc(nmemb * size);
        }
        resolve_real_symbols();
    }
    atomic_fetch_add(&rogue_probe_calloc_calls, 1ULL);
    atomic_fetch_add(&rogue_probe_bytes_requested, (unsigned long long)(nmemb * size));
    return real_calloc(nmemb, size);
}

void *realloc(void *ptr, size_t size) {
    if (is_bootstrap_ptr(ptr)) {
        /* The bootstrap pool never tracks individual allocation sizes, so a
         * realloc of a bootstrap address is served as a fresh allocation
         * with a bounded best-effort copy from the original address. */
        unsigned char *candidate = (unsigned char *)ptr;
        size_t available = (size_t)(bootstrap_pool + BOOTSTRAP_POOL_BYTES - candidate);
        size_t copy_bytes = size < available ? size : available;
        void *new_ptr = malloc(size);
        if (new_ptr != NULL && copy_bytes > 0) {
            memcpy(new_ptr, ptr, copy_bytes);
        }
        return new_ptr;
    }
    if (real_realloc == NULL) {
        if (in_dlsym) {
            return bootstrap_alloc(size);
        }
        resolve_real_symbols();
    }
    atomic_fetch_add(&rogue_probe_realloc_calls, 1ULL);
    atomic_fetch_add(&rogue_probe_bytes_requested, (unsigned long long)size);
    return real_realloc(ptr, size);
}

int posix_memalign(void **memptr, size_t alignment, size_t size) {
    if (real_posix_memalign == NULL) {
        if (in_dlsym) {
            void *ptr = bootstrap_alloc(size);
            if (ptr == NULL) {
                return ENOMEM;
            }
            *memptr = ptr;
            return 0;
        }
        resolve_real_symbols();
    }
    atomic_fetch_add(&rogue_probe_aligned_calls, 1ULL);
    atomic_fetch_add(&rogue_probe_bytes_requested, (unsigned long long)size);
    return real_posix_memalign(memptr, alignment, size);
}

void *aligned_alloc(size_t alignment, size_t size) {
    if (real_aligned_alloc == NULL) {
        if (in_dlsym) {
            return bootstrap_alloc(size);
        }
        resolve_real_symbols();
    }
    atomic_fetch_add(&rogue_probe_aligned_calls, 1ULL);
    atomic_fetch_add(&rogue_probe_bytes_requested, (unsigned long long)size);
    return real_aligned_alloc(alignment, size);
}

static void write_kv_line(int fd, const char *key, unsigned long long value) {
    char buf[128];
    int len = snprintf(buf, sizeof(buf), "%s %llu\n", key, value);
    if (len > 0) {
        ssize_t written = write(fd, buf, (size_t)len);
        (void)written;
    }
}

/*
 * Dumps every counter at process exit through a destructor routine, using
 * only write-time-safe operations (open/write/close, no buffered stdio)
 * since a destructor runs very late in process teardown. Writes to the path
 * named by ROGUE_PROBE_ALLOC_OUT, or to standard error when that variable
 * is unset.
 */
__attribute__((destructor)) static void rogue_probe_dump_counts(void) {
    const char *out_path = getenv("ROGUE_PROBE_ALLOC_OUT");
    int fd = STDERR_FILENO;
    int close_fd = 0;

    if (out_path != NULL) {
        int opened = open(out_path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
        if (opened >= 0) {
            fd = opened;
            close_fd = 1;
        }
    }

    write_kv_line(fd, "malloc_calls", atomic_load(&rogue_probe_malloc_calls));
    write_kv_line(fd, "free_calls", atomic_load(&rogue_probe_free_calls));
    write_kv_line(fd, "calloc_calls", atomic_load(&rogue_probe_calloc_calls));
    write_kv_line(fd, "realloc_calls", atomic_load(&rogue_probe_realloc_calls));
    write_kv_line(fd, "aligned_calls", atomic_load(&rogue_probe_aligned_calls));
    write_kv_line(fd, "bytes_requested", atomic_load(&rogue_probe_bytes_requested));

    if (close_fd) {
        close(fd);
    }
}
