/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Test-only fake AxiStreamDma driver syscall interposer.
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
#include "fake_axi_dma_driver.h"

#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdarg.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <unistd.h>

#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <map>
#include <mutex>
#include <set>
#include <thread>

#include "rogue/hardware/drivers/DmaDriver.h"

#ifndef MAP_ANON
    #define MAP_ANON MAP_ANONYMOUS
#endif

namespace {

constexpr const char* FakePathPrefix = "/tmp/rogue-cpp-fake-axi-dma";
constexpr const char* FakeBackingPrefix = "/tmp/rogue-cpp-fake-axi-dma-backing";
constexpr uint32_t FakeBuffCount     = 4;
constexpr uint32_t FakeBuffSize      = 4096;

struct FakeState {
    std::mutex mtx;
    std::condition_variable cv;
    std::set<int> fakeFds;
    std::map<void*, size_t> fakeMappings;
    RogueFakeAxiDmaBlockOp blockNext = ROGUE_FAKE_AXI_DMA_BLOCK_NONE;
    bool blocked                     = false;
    bool releaseBlocked              = false;
    uint32_t activeDriverCalls       = 0;
    uint32_t closeCount              = 0;
    uint32_t munmapCount             = 0;
    uint32_t retIndexCount           = 0;
    uint32_t nextIndex               = 0;
    bool closeDuringDriverCall       = false;
};

FakeState& state() {
    static FakeState* fakeState = new FakeState;
    return *fakeState;
}

template <typename Func>
Func realSymbol(const char* name) {
    void* sym = dlsym(RTLD_NEXT, name);
    return reinterpret_cast<Func>(sym);
}

using OpenFn   = int (*)(const char*, int, ...);
using CloseFn  = int (*)(int);
using IoctlFn  = int (*)(int, unsigned long, ...);
using MmapFn   = void* (*)(void*, size_t, int, int, int, off_t);
using MunmapFn = int (*)(void*, size_t);
using PollFn   = int (*)(struct pollfd*, nfds_t, int);
using ReadFn   = ssize_t (*)(int, void*, size_t);
using WriteFn  = ssize_t (*)(int, const void*, size_t);

OpenFn realOpen() {
    static OpenFn fn = realSymbol<OpenFn>("open");
    return fn;
}

#ifndef __APPLE__
OpenFn realOpen64() {
    static OpenFn fn = realSymbol<OpenFn>("open64");
    return fn;
}
#endif

CloseFn realClose() {
    static CloseFn fn = realSymbol<CloseFn>("close");
    return fn;
}

IoctlFn realIoctl() {
    static IoctlFn fn = realSymbol<IoctlFn>("ioctl");
    return fn;
}

MmapFn realMmap() {
    static MmapFn fn = realSymbol<MmapFn>("mmap");
    return fn;
}

MunmapFn realMunmap() {
    static MunmapFn fn = realSymbol<MunmapFn>("munmap");
    return fn;
}

PollFn realPoll() {
    static PollFn fn = realSymbol<PollFn>("poll");
    return fn;
}

ReadFn realRead() {
    static ReadFn fn = realSymbol<ReadFn>("read");
    return fn;
}

WriteFn realWrite() {
    static WriteFn fn = realSymbol<WriteFn>("write");
    return fn;
}

int callRealOpen(const char* path, int flags, mode_t mode, bool hasMode) {
#ifdef __APPLE__
    return static_cast<int>(syscall(SYS_open, path, flags, hasMode ? mode : 0));
#else
    if (hasMode) return realOpen()(path, flags, mode);
    return realOpen()(path, flags);
#endif
}

int callRealClose(int fd) {
#ifdef __APPLE__
    return static_cast<int>(syscall(SYS_close, fd));
#else
    return realClose()(fd);
#endif
}

void* callRealMmap(void* addr, size_t length, int prot, int flags, int fd, off_t offset) {
#ifdef __APPLE__
    return reinterpret_cast<void*>(syscall(SYS_mmap, addr, length, prot, flags, fd, offset));
#else
    return realMmap()(addr, length, prot, flags, fd, offset);
#endif
}

int callRealMunmap(void* addr, size_t length) {
#ifdef __APPLE__
    return static_cast<int>(syscall(SYS_munmap, addr, length));
#else
    return realMunmap()(addr, length);
#endif
}

int callRealPoll(struct pollfd* fds, nfds_t nfds, int timeout) {
#ifdef __APPLE__
    return static_cast<int>(syscall(SYS_poll, fds, nfds, timeout));
#else
    return realPoll()(fds, nfds, timeout);
#endif
}

ssize_t callRealRead(int fd, void* buf, size_t count) {
#ifdef __APPLE__
    return static_cast<ssize_t>(syscall(SYS_read, fd, buf, count));
#else
    return realRead()(fd, buf, count);
#endif
}

ssize_t callRealWrite(int fd, const void* buf, size_t count) {
#ifdef __APPLE__
    return static_cast<ssize_t>(syscall(SYS_write, fd, buf, count));
#else
    return realWrite()(fd, buf, count);
#endif
}

bool isFakePath(const char* path) {
    return (path != nullptr) && (strncmp(path, FakePathPrefix, strlen(FakePathPrefix)) == 0);
}

bool isFakeFdLocked(int fd) {
    return state().fakeFds.find(fd) != state().fakeFds.end();
}

bool isFakeFd(int fd) {
    FakeState& st = state();
    std::lock_guard<std::mutex> lock(st.mtx);
    return isFakeFdLocked(fd);
}

void maybeBlock(RogueFakeAxiDmaBlockOp op) {
    FakeState& st = state();
    std::unique_lock<std::mutex> lock(st.mtx);
    if (st.blockNext != op) return;

    st.blockNext      = ROGUE_FAKE_AXI_DMA_BLOCK_NONE;
    st.blocked        = true;
    st.releaseBlocked = false;
    st.cv.notify_all();
    st.cv.wait(lock, [&st] { return st.releaseBlocked; });
    st.blocked        = false;
    st.releaseBlocked = false;
    st.cv.notify_all();
}

class DriverCall {
  public:
    explicit DriverCall(bool enabled) : enabled_(enabled) {
        if (enabled_) {
            FakeState& st = state();
            std::lock_guard<std::mutex> lock(st.mtx);
            st.activeDriverCalls++;
        }
    }

    ~DriverCall() {
        if (enabled_) {
            FakeState& st = state();
            std::lock_guard<std::mutex> lock(st.mtx);
            st.activeDriverCalls--;
            st.cv.notify_all();
        }
    }

  private:
    bool enabled_;
};

int fakeOpenImpl(const char* path, int flags, mode_t mode, bool hasMode) {
    if (!isFakePath(path)) {
        return callRealOpen(path, flags, mode, hasMode);
    }

    char backingPath[256];
    snprintf(backingPath, sizeof(backingPath), "%s-%d-%ld", FakeBackingPrefix, getpid(), random());
    int fd = callRealOpen(backingPath, O_RDWR | O_CREAT | O_TRUNC, 0600, true);
    if (fd >= 0) {
        static_cast<void>(unlink(backingPath));
        static_cast<void>(ftruncate(fd, FakeBuffCount * FakeBuffSize));
        FakeState& st = state();
        std::lock_guard<std::mutex> lock(st.mtx);
        st.fakeFds.insert(fd);
    }
    return fd;
}

int fakeIoctlImpl(int fd, unsigned long request, va_list args) {
    if (!isFakeFd(fd)) {
        void* arg = va_arg(args, void*);
#ifdef __APPLE__
        return static_cast<int>(syscall(SYS_ioctl, fd, request, arg));
#else
        return realIoctl()(fd, request, arg);
#endif
    }

    DriverCall call(true);

    switch (request) {
        case DMA_Get_Version:
            return DMA_VERSION;
        case DMA_Get_Buff_Count:
            return FakeBuffCount;
        case DMA_Get_Buff_Size:
            maybeBlock(ROGUE_FAKE_AXI_DMA_BLOCK_IOCTL_BUFF_SIZE);
            return FakeBuffSize;
        case DMA_Get_TxBuff_Count:
        case DMA_Get_RxBuff_Count:
            return 2;
        case DMA_Get_TxBuffinUser_Count:
        case DMA_Get_TxBuffinHW_Count:
        case DMA_Get_TxBuffinPreHWQ_Count:
        case DMA_Get_TxBuffinSWQ_Count:
        case DMA_Get_TxBuffMiss_Count:
        case DMA_Get_RxBuffinUser_Count:
        case DMA_Get_RxBuffinHW_Count:
        case DMA_Get_RxBuffinPreHWQ_Count:
        case DMA_Get_RxBuffinSWQ_Count:
        case DMA_Get_RxBuffMiss_Count:
            return 0;
        case DMA_Get_Index: {
            maybeBlock(ROGUE_FAKE_AXI_DMA_BLOCK_IOCTL_GET_INDEX);
            FakeState& st = state();
            std::lock_guard<std::mutex> lock(st.mtx);
            const uint32_t ret = st.nextIndex;
            st.nextIndex       = (st.nextIndex + 1) % FakeBuffCount;
            return static_cast<int>(ret);
        }
        case DMA_Ret_Index | 0x10000:
            static_cast<void>(va_arg(args, void*));
            maybeBlock(ROGUE_FAKE_AXI_DMA_BLOCK_IOCTL_RET_INDEX);
            {
                FakeState& st = state();
                std::lock_guard<std::mutex> lock(st.mtx);
                st.retIndexCount++;
            }
            return 0;
        case DMA_Set_MaskBytes:
            static_cast<void>(va_arg(args, void*));
            return 0;
        case DMA_Get_GITV: {
            char* gitv = va_arg(args, char*);
            if (gitv != nullptr) strncpy(gitv, "fake-axi-dma", 31);
            return 0;
        }
        case DMA_Set_Debug:
        case DMA_Set_Mask:
            return 0;
        default:
            return 0;
    }
}

void* fakeMmapImpl(void* addr, size_t length, int prot, int flags, int fd, off_t offset) {
    if (!isFakeFd(fd)) return callRealMmap(addr, length, prot, flags, fd, offset);

    void* ptr = callRealMmap(nullptr, length, prot, MAP_PRIVATE | MAP_ANON, -1, 0);
    if (ptr != MAP_FAILED) {
        FakeState& st = state();
        std::lock_guard<std::mutex> lock(st.mtx);
        st.fakeMappings[ptr] = length;
    }
    return ptr;
}

int fakeMunmapImpl(void* addr, size_t length) {
    {
        FakeState& st = state();
        std::lock_guard<std::mutex> lock(st.mtx);
        auto it = st.fakeMappings.find(addr);
        if (it != st.fakeMappings.end()) {
            length = it->second;
            st.fakeMappings.erase(it);
            st.munmapCount++;
        } else if (length == FakeBuffSize) {
            st.munmapCount++;
        }
    }
    return callRealMunmap(addr, length);
}

int fakeCloseImpl(int fd) {
    bool fake = false;
    {
        FakeState& st = state();
        std::lock_guard<std::mutex> lock(st.mtx);
        auto it = st.fakeFds.find(fd);
        fake    = (it != st.fakeFds.end());
        if (fake) {
            st.fakeFds.erase(it);
            st.closeCount++;
            if (st.activeDriverCalls != 0) st.closeDuringDriverCall = true;
        }
    }
    return callRealClose(fd);
}

int fakePollImpl(struct pollfd* fds, nfds_t nfds, int timeout) {
    bool allFake = true;

    for (nfds_t i = 0; i < nfds; ++i) {
        if (!isFakeFd(fds[i].fd)) {
            allFake = false;
            break;
        }
    }

    if (!allFake) return callRealPoll(fds, nfds, timeout);

    int ready = 0;
    for (nfds_t i = 0; i < nfds; ++i) {
        fds[i].revents = 0;
        if ((fds[i].events & POLLOUT) != 0) {
            fds[i].revents = POLLOUT;
            ready++;
        }
    }

    if (ready == 0) {
        const int sleepMs = (timeout < 0) ? 1 : timeout;
        if (sleepMs > 0) std::this_thread::sleep_for(std::chrono::milliseconds(sleepMs));
    }
    return ready;
}

ssize_t fakeReadImpl(int fd, void* buf, size_t count) {
    if (!isFakeFd(fd)) return callRealRead(fd, buf, count);
    DriverCall call(true);
    return 0;
}

ssize_t fakeWriteImpl(int fd, const void* buf, size_t count) {
    if (!isFakeFd(fd)) return callRealWrite(fd, buf, count);
    DriverCall call(true);
    maybeBlock(ROGUE_FAKE_AXI_DMA_BLOCK_WRITE);
    return static_cast<ssize_t>(count);
}

#ifdef __APPLE__
    #define ROGUE_DYLD_INTERPOSE(replacement, replacee)                       \
        __attribute__((used)) static struct {                                 \
            const void* replacementFunc;                                      \
            const void* replaceeFunc;                                         \
        } _rogue_interpose_##replacee __attribute__((section("__DATA,__interpose"))) = { \
            reinterpret_cast<const void*>(replacement), reinterpret_cast<const void*>(replacee)}
#endif

}  // namespace

extern "C" const char* rogue_fake_axi_dma_path_prefix() {
    return FakePathPrefix;
}

extern "C" void rogue_fake_axi_dma_reset() {
    FakeState& st = state();
    std::lock_guard<std::mutex> lock(st.mtx);
    st.blockNext             = ROGUE_FAKE_AXI_DMA_BLOCK_NONE;
    st.blocked               = false;
    st.releaseBlocked        = false;
    st.activeDriverCalls     = 0;
    st.closeCount            = 0;
    st.munmapCount           = 0;
    st.retIndexCount         = 0;
    st.nextIndex             = 0;
    st.closeDuringDriverCall = false;
}

extern "C" void rogue_fake_axi_dma_block_next(RogueFakeAxiDmaBlockOp op) {
    FakeState& st = state();
    std::lock_guard<std::mutex> lock(st.mtx);
    st.blockNext      = op;
    st.blocked        = false;
    st.releaseBlocked = false;
}

extern "C" bool rogue_fake_axi_dma_wait_blocked(uint32_t timeoutMs) {
    FakeState& st = state();
    std::unique_lock<std::mutex> lock(st.mtx);
    return st.cv.wait_for(lock, std::chrono::milliseconds(timeoutMs), [&st] { return st.blocked; });
}

extern "C" void rogue_fake_axi_dma_release_blocked() {
    FakeState& st = state();
    std::lock_guard<std::mutex> lock(st.mtx);
    st.releaseBlocked = true;
    st.cv.notify_all();
}

extern "C" uint32_t rogue_fake_axi_dma_close_count() {
    FakeState& st = state();
    std::lock_guard<std::mutex> lock(st.mtx);
    return st.closeCount;
}

extern "C" uint32_t rogue_fake_axi_dma_munmap_count() {
    FakeState& st = state();
    std::lock_guard<std::mutex> lock(st.mtx);
    return st.munmapCount;
}

extern "C" uint32_t rogue_fake_axi_dma_ret_index_count() {
    FakeState& st = state();
    std::lock_guard<std::mutex> lock(st.mtx);
    return st.retIndexCount;
}

extern "C" bool rogue_fake_axi_dma_close_during_driver_call() {
    FakeState& st = state();
    std::lock_guard<std::mutex> lock(st.mtx);
    return st.closeDuringDriverCall;
}

extern "C" int rogue_fake_open(const char* path, int flags, ...) {
    mode_t mode  = 0;
    bool hasMode = (flags & O_CREAT) != 0;
    if (hasMode) {
        va_list args;
        va_start(args, flags);
        mode = static_cast<mode_t>(va_arg(args, int));
        va_end(args);
    }
    return fakeOpenImpl(path, flags, mode, hasMode);
}

extern "C" int rogue_fake_close(int fd) {
    return fakeCloseImpl(fd);
}

extern "C" int rogue_fake_ioctl(int fd, unsigned long request, ...) {
    va_list args;
    va_start(args, request);
    int ret = fakeIoctlImpl(fd, request, args);
    va_end(args);
    return ret;
}

extern "C" void* rogue_fake_mmap(void* addr, size_t length, int prot, int flags, int fd, off_t offset) {
    return fakeMmapImpl(addr, length, prot, flags, fd, offset);
}

extern "C" int rogue_fake_munmap(void* addr, size_t length) {
    return fakeMunmapImpl(addr, length);
}

extern "C" int rogue_fake_poll(struct pollfd* fds, nfds_t nfds, int timeout) {
    return fakePollImpl(fds, nfds, timeout);
}

extern "C" ssize_t rogue_fake_read(int fd, void* buf, size_t count) {
    return fakeReadImpl(fd, buf, count);
}

extern "C" ssize_t rogue_fake_write(int fd, const void* buf, size_t count) {
    return fakeWriteImpl(fd, buf, count);
}

#ifdef __APPLE__
ROGUE_DYLD_INTERPOSE(rogue_fake_open, open);
ROGUE_DYLD_INTERPOSE(rogue_fake_close, close);
ROGUE_DYLD_INTERPOSE(rogue_fake_ioctl, ioctl);
ROGUE_DYLD_INTERPOSE(rogue_fake_munmap, munmap);
ROGUE_DYLD_INTERPOSE(rogue_fake_poll, poll);
#else
extern "C" int open(const char* path, int flags, ...) {
    mode_t mode  = 0;
    bool hasMode = (flags & O_CREAT) != 0;
    if (hasMode) {
        va_list args;
        va_start(args, flags);
        mode = static_cast<mode_t>(va_arg(args, int));
        va_end(args);
    }
    return fakeOpenImpl(path, flags, mode, hasMode);
}

extern "C" int open64(const char* path, int flags, ...) {
    mode_t mode  = 0;
    bool hasMode = (flags & O_CREAT) != 0;
    if (hasMode) {
        va_list args;
        va_start(args, flags);
        mode = static_cast<mode_t>(va_arg(args, int));
        va_end(args);
    }

    if (isFakePath(path)) return fakeOpenImpl(path, flags, mode, hasMode);
    if (hasMode) return realOpen64()(path, flags, mode);
    return realOpen64()(path, flags);
}

extern "C" int close(int fd) {
    return fakeCloseImpl(fd);
}

extern "C" int ioctl(int fd, unsigned long request, ...) {
    va_list args;
    va_start(args, request);
    int ret = fakeIoctlImpl(fd, request, args);
    va_end(args);
    return ret;
}

extern "C" void* mmap(void* addr, size_t length, int prot, int flags, int fd, off_t offset) {
    return fakeMmapImpl(addr, length, prot, flags, fd, offset);
}

extern "C" int munmap(void* addr, size_t length) {
    return fakeMunmapImpl(addr, length);
}

extern "C" int poll(struct pollfd* fds, nfds_t nfds, int timeout) {
    return fakePollImpl(fds, nfds, timeout);
}

extern "C" ssize_t read(int fd, void* buf, size_t count) {
    return fakeReadImpl(fd, buf, count);
}

extern "C" ssize_t write(int fd, const void* buf, size_t count) {
    return fakeWriteImpl(fd, buf, count);
}
#endif
