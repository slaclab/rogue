/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Test-only LD_PRELOAD shim that emulates just enough of the aes-stream-driver
 * character device for AxiStreamDma to construct, hand out a zero-copy buffer,
 * and tear down on a machine with no DMA hardware. It intercepts
 * open/close/ioctl/mmap/munmap/poll for a single sentinel device path and
 * backs the "DMA" buffers with ordinary anonymous mappings, tracking how many
 * are currently mapped. The test queries that count via fakedma_mapped_count()
 * to prove that AxiStreamDma keeps the shared mapping alive across stop() and
 * releases it only at destruction.
 *
 * This object is built only under -DROGUE_BUILD_TESTS=ON and is never linked
 * into rogue-core or shipped.
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
#include <fcntl.h>
#include <poll.h>
#include <pthread.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <unistd.h>

/*
 * DMA ioctl request codes and version. These mirror the stable kernel ABI in
 * include/rogue/hardware/drivers/DmaDriver.h (which is C++-only and cannot be
 * included here). Keep in sync with that header.
 */
#define FAKE_DMA_Get_Buff_Count   0x1001
#define FAKE_DMA_Get_Buff_Size    0x1002
#define FAKE_DMA_Ret_Index        0x1005
#define FAKE_DMA_Get_Index        0x1006
#define FAKE_DMA_Set_MaskBytes    0x1008
#define FAKE_DMA_Get_Version      0x1009
#define FAKE_DMA_Get_RxBuff_Count 0x100C
#define FAKE_DMA_Get_TxBuff_Count 0x100D
#define FAKE_DMA_VERSION          0x06

/* Sentinel device path intercepted by this shim. */
#define FAKE_PATH       "/tmp/rogue-fake-datadev"
#define FAKE_BUFF_SIZE  4096u
#define FAKE_BUFF_COUNT 8u

#define MAX_FDS     16
#define MAX_REGIONS 64

static pthread_mutex_t g_lock = PTHREAD_MUTEX_INITIALIZER;

static int g_fds[MAX_FDS];
static int g_fd_n = 0;

static void*  g_region_addr[MAX_REGIONS];
static size_t g_region_len[MAX_REGIONS];
static int    g_region_n = 0;

static int      g_mapped_count = 0;
static uint32_t g_next_index   = 0;

typedef int (*open_fn)(const char*, int, ...);
typedef void* (*mmap_fn)(void*, size_t, int, int, int, off_t);
typedef int (*munmap_fn)(void*, size_t);
typedef int (*close_fn)(int);
typedef int (*ioctl_fn)(int, unsigned long, ...);
typedef int (*poll_fn)(struct pollfd*, nfds_t, int);

static open_fn   real_open;
static open_fn   real_open64;
static mmap_fn   real_mmap;
static mmap_fn   real_mmap64;
static munmap_fn real_munmap;
static close_fn  real_close;
static ioctl_fn  real_ioctl;
static poll_fn   real_poll;

/* ------- bookkeeping helpers (caller holds g_lock) ------- */

static int is_our_fd_locked(int fd) {
    int i;
    for (i = 0; i < g_fd_n; i++)
        if (g_fds[i] == fd) return 1;
    return 0;
}

static void add_fd_locked(int fd) {
    if (g_fd_n < MAX_FDS) g_fds[g_fd_n++] = fd;
}

static void del_fd_locked(int fd) {
    int i;
    for (i = 0; i < g_fd_n; i++) {
        if (g_fds[i] == fd) {
            g_fds[i] = g_fds[--g_fd_n];
            return;
        }
    }
}

static void add_region_locked(void* addr, size_t len) {
    if (g_region_n < MAX_REGIONS) {
        g_region_addr[g_region_n] = addr;
        g_region_len[g_region_n]  = len;
        g_region_n++;
        g_mapped_count++;
    }
}

static int del_region_locked(void* addr) {
    int i;
    for (i = 0; i < g_region_n; i++) {
        if (g_region_addr[i] == addr) {
            g_region_addr[i] = g_region_addr[g_region_n - 1];
            g_region_len[i]  = g_region_len[g_region_n - 1];
            g_region_n--;
            g_mapped_count--;
            return 1;
        }
    }
    return 0;
}

/* Return an anonymous mapping standing in for a DMA buffer, and record it. */
static void* make_fake_buffer(size_t len, int prot) {
    void* p = real_mmap(NULL, len, prot, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p != MAP_FAILED) {
        pthread_mutex_lock(&g_lock);
        add_region_locked(p, len);
        pthread_mutex_unlock(&g_lock);
    }
    return p;
}

/* ------- intercepted entry points ------- */

int open(const char* path, int flags, ...) {
    mode_t mode = 0;
    if (!real_open) real_open = (open_fn)dlsym(RTLD_NEXT, "open");

    if (flags & O_CREAT) {
        va_list ap;
        va_start(ap, flags);
        mode = (mode_t)va_arg(ap, int);
        va_end(ap);
    }

    if (path != NULL && strcmp(path, FAKE_PATH) == 0) {
        int fd = real_open("/dev/null", O_RDWR);
        if (fd >= 0) {
            pthread_mutex_lock(&g_lock);
            add_fd_locked(fd);
            pthread_mutex_unlock(&g_lock);
        }
        return fd;
    }
    return real_open(path, flags, mode);
}

int open64(const char* path, int flags, ...) {
    mode_t mode = 0;
    if (!real_open64) real_open64 = (open_fn)dlsym(RTLD_NEXT, "open64");

    if (flags & O_CREAT) {
        va_list ap;
        va_start(ap, flags);
        mode = (mode_t)va_arg(ap, int);
        va_end(ap);
    }

    if (path != NULL && strcmp(path, FAKE_PATH) == 0) {
        int fd = real_open64("/dev/null", O_RDWR);
        if (fd >= 0) {
            pthread_mutex_lock(&g_lock);
            add_fd_locked(fd);
            pthread_mutex_unlock(&g_lock);
        }
        return fd;
    }
    return real_open64(path, flags, mode);
}

int close(int fd) {
    if (!real_close) real_close = (close_fn)dlsym(RTLD_NEXT, "close");
    pthread_mutex_lock(&g_lock);
    del_fd_locked(fd);
    pthread_mutex_unlock(&g_lock);
    return real_close(fd);
}

void* mmap(void* addr, size_t len, int prot, int flags, int fd, off_t off) {
    int ours;
    if (!real_mmap) {
        static __thread int resolving = 0;
        if (resolving) return (void*)syscall(SYS_mmap, addr, len, prot, flags, fd, off);
        resolving  = 1;
        real_mmap  = (mmap_fn)dlsym(RTLD_NEXT, "mmap");
        resolving  = 0;
    }
    pthread_mutex_lock(&g_lock);
    ours = is_our_fd_locked(fd);
    pthread_mutex_unlock(&g_lock);

    if (ours) return make_fake_buffer(len, prot);
    return real_mmap(addr, len, prot, flags, fd, off);
}

void* mmap64(void* addr, size_t len, int prot, int flags, int fd, off_t off) {
    int ours;
    if (!real_mmap64) {
        static __thread int resolving = 0;
        if (resolving) return (void*)syscall(SYS_mmap, addr, len, prot, flags, fd, off);
        resolving    = 1;
        real_mmap64  = (mmap_fn)dlsym(RTLD_NEXT, "mmap64");
        resolving    = 0;
    }
    if (!real_mmap) real_mmap = (mmap_fn)dlsym(RTLD_NEXT, "mmap");

    pthread_mutex_lock(&g_lock);
    ours = is_our_fd_locked(fd);
    pthread_mutex_unlock(&g_lock);

    if (ours) return make_fake_buffer(len, prot);
    return real_mmap64(addr, len, prot, flags, fd, off);
}

int munmap(void* addr, size_t len) {
    if (!real_munmap) {
        static __thread int resolving = 0;
        if (resolving) return (int)syscall(SYS_munmap, addr, len);
        resolving    = 1;
        real_munmap  = (munmap_fn)dlsym(RTLD_NEXT, "munmap");
        resolving    = 0;
    }
    pthread_mutex_lock(&g_lock);
    del_region_locked(addr);
    pthread_mutex_unlock(&g_lock);
    return real_munmap(addr, len);
}

int ioctl(int fd, unsigned long request, ...) {
    void* arg;
    va_list ap;
    int ours;
    if (!real_ioctl) real_ioctl = (ioctl_fn)dlsym(RTLD_NEXT, "ioctl");

    va_start(ap, request);
    arg = va_arg(ap, void*);
    va_end(ap);

    pthread_mutex_lock(&g_lock);
    ours = is_our_fd_locked(fd);
    pthread_mutex_unlock(&g_lock);

    if (!ours) return real_ioctl(fd, request, arg);

    switch (request & 0xFFFF) {
        case FAKE_DMA_Get_Version:      return FAKE_DMA_VERSION;
        case FAKE_DMA_Get_Buff_Size:    return (int)FAKE_BUFF_SIZE;
        case FAKE_DMA_Get_Buff_Count:   return (int)FAKE_BUFF_COUNT;
        case FAKE_DMA_Get_RxBuff_Count: return (int)(FAKE_BUFF_COUNT / 2);
        case FAKE_DMA_Get_TxBuff_Count: return (int)(FAKE_BUFF_COUNT / 2);
        case FAKE_DMA_Set_MaskBytes:    return 0;
        case FAKE_DMA_Get_Index: {
            int idx;
            pthread_mutex_lock(&g_lock);
            idx = (int)(g_next_index++ % FAKE_BUFF_COUNT);
            pthread_mutex_unlock(&g_lock);
            return idx;
        }
        case FAKE_DMA_Ret_Index: return 0;
        default:                 return 0;
    }
}

int poll(struct pollfd* fds, nfds_t nfds, int timeout) {
    if (!real_poll) real_poll = (poll_fn)dlsym(RTLD_NEXT, "poll");

    if (nfds == 1 && fds != NULL) {
        int ours;
        pthread_mutex_lock(&g_lock);
        ours = is_our_fd_locked(fds[0].fd);
        pthread_mutex_unlock(&g_lock);

        if (ours) {
            /* TX/alloc path waits for POLLOUT: report ready so acceptReq/
             * acceptFrame proceed to dmaGetIndex/dmaWrite. */
            if (fds[0].events & POLLOUT) {
                fds[0].revents = POLLOUT;
                return 1;
            }
            /* RX path waits for POLLIN: stay idle for the requested timeout and
             * report nothing so the worker thread never issues a read. */
            if (timeout > 0) real_poll(NULL, 0, timeout);
            fds[0].revents = 0;
            return 0;
        }
    }
    return real_poll(fds, nfds, timeout);
}

/* Query hook for the test: number of fake DMA buffers currently mapped. */
int fakedma_mapped_count(void) {
    int n;
    pthread_mutex_lock(&g_lock);
    n = g_mapped_count;
    pthread_mutex_unlock(&g_lock);
    return n;
}
