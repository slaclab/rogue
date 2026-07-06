/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Native C++ lifecycle tests for AxiStreamDma stop/fd races using a fake DMA
 * syscall backend.
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
#include <stdint.h>
#include <dlfcn.h>
#include <unistd.h>

#include <atomic>
#include <chrono>
#include <cstdlib>
#include <functional>
#include <memory>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

#include "doctest/doctest.h"
#include "fake_axi_dma_driver.h"
#include "rogue/GeneralError.h"
#include "rogue/hardware/axi/AxiStreamDma.h"
#include "rogue/interfaces/stream/Frame.h"
#include "support/test_helpers.h"

namespace rha = rogue::hardware::axi;
namespace ris = rogue::interfaces::stream;

namespace {

class FakeAxiDmaDriver {
  public:
    using PathPrefixFn       = const char* (*)();
    using ResetFn            = void (*)();
    using BlockNextFn        = void (*)(RogueFakeAxiDmaBlockOp);
    using WaitBlockedFn      = bool (*)(uint32_t);
    using ReleaseBlockedFn   = void (*)();
    using CountFn            = uint32_t (*)();
    using CloseDuringCallFn  = bool (*)();

    FakeAxiDmaDriver() {
        const char* path = std::getenv("ROGUE_FAKE_AXI_DMA_DRIVER_LIB");
        if (path == nullptr) throw std::runtime_error("ROGUE_FAKE_AXI_DMA_DRIVER_LIB is not set");

        handle_ = dlopen(path, RTLD_NOW | RTLD_GLOBAL);
        if (handle_ == nullptr) throw std::runtime_error(dlerror());

        pathPrefix_       = load<PathPrefixFn>("rogue_fake_axi_dma_path_prefix");
        reset_            = load<ResetFn>("rogue_fake_axi_dma_reset");
        blockNext_        = load<BlockNextFn>("rogue_fake_axi_dma_block_next");
        waitBlocked_      = load<WaitBlockedFn>("rogue_fake_axi_dma_wait_blocked");
        releaseBlocked_   = load<ReleaseBlockedFn>("rogue_fake_axi_dma_release_blocked");
        closeCount_       = load<CountFn>("rogue_fake_axi_dma_close_count");
        munmapCount_      = load<CountFn>("rogue_fake_axi_dma_munmap_count");
        retIndexCount_    = load<CountFn>("rogue_fake_axi_dma_ret_index_count");
        closeDuringCall_  = load<CloseDuringCallFn>("rogue_fake_axi_dma_close_during_driver_call");
    }

    const char* pathPrefix() const { return pathPrefix_(); }
    void reset() const { reset_(); }
    void blockNext(RogueFakeAxiDmaBlockOp op) const { blockNext_(op); }
    bool waitBlocked(uint32_t timeoutMs) const { return waitBlocked_(timeoutMs); }
    void releaseBlocked() const { releaseBlocked_(); }
    uint32_t closeCount() const { return closeCount_(); }
    uint32_t munmapCount() const { return munmapCount_(); }
    uint32_t retIndexCount() const { return retIndexCount_(); }
    bool closeDuringDriverCall() const { return closeDuringCall_(); }

  private:
    template <typename Func>
    Func load(const char* name) {
        void* sym = dlsym(handle_, name);
        if (sym == nullptr) throw std::runtime_error(dlerror());
        return reinterpret_cast<Func>(sym);
    }

    void* handle_;
    PathPrefixFn pathPrefix_;
    ResetFn reset_;
    BlockNextFn blockNext_;
    WaitBlockedFn waitBlocked_;
    ReleaseBlockedFn releaseBlocked_;
    CountFn closeCount_;
    CountFn munmapCount_;
    CountFn retIndexCount_;
    CloseDuringCallFn closeDuringCall_;
};

FakeAxiDmaDriver& fakeDriver() {
    static FakeAxiDmaDriver driver;
    return driver;
}

std::string fakePath(const char* name) {
    static std::atomic<uint32_t> counter{0};
    return std::string(fakeDriver().pathPrefix()) + "-" + name + "-" + std::to_string(getpid()) + "-" +
           std::to_string(counter.fetch_add(1));
}

rha::AxiStreamDmaPtr makeDma(const char* name) {
    return rha::AxiStreamDma::create(fakePath(name), 0, false);
}

void requireStopWaitsWhileBlocked(const std::function<void()>& stopCall, const std::atomic<bool>& stopDone) {
    std::this_thread::sleep_for(std::chrono::milliseconds(25));
    CHECK_FALSE(stopDone.load());
    CHECK_FALSE(fakeDriver().closeDuringDriverCall());
    stopCall();
}

void checkStopWaitsForBlockedDriverCall(const rha::AxiStreamDmaPtr& dma,
                                        RogueFakeAxiDmaBlockOp blockOp,
                                        const std::function<void()>& call) {
    fakeDriver().blockNext(blockOp);

    std::atomic<bool> callDone{false};
    std::thread caller([&] {
        call();
        callDone.store(true);
    });

    REQUIRE(fakeDriver().waitBlocked(1000));
    CHECK_FALSE(callDone.load());

    std::atomic<bool> stopDone{false};
    std::thread stopper([&] {
        dma->stop();
        stopDone.store(true);
    });

    requireStopWaitsWhileBlocked([&] { fakeDriver().releaseBlocked(); }, stopDone);

    caller.join();
    stopper.join();

    CHECK(callDone.load());
    CHECK(stopDone.load());
    CHECK_FALSE(fakeDriver().closeDuringDriverCall());
}

}  // namespace

TEST_CASE("AxiStreamDma stop keeps shared zero-copy mappings alive until destruction") {
    fakeDriver().reset();

    auto dma   = makeDma("mapping-lifetime");
    auto frame = dma->acceptReq(64, true);

    REQUIRE_EQ(frame->bufferCount(), 1U);
    CHECK_EQ(fakeDriver().munmapCount(), 0U);

    dma->stop();

    // Before this branch, stop() called closeShared(), which unmapped the DMA
    // pages even though downstream Rogue frames could still hold buffers that
    // point into those pages.
    CHECK_EQ(fakeDriver().munmapCount(), 0U);

    frame->clear();
    CHECK_EQ(fakeDriver().munmapCount(), 0U);

    dma.reset();
    CHECK_EQ(fakeDriver().munmapCount(), 4U);
}

TEST_CASE("AxiStreamDma rejects new stream work after stop while retaining shared descriptor") {
    fakeDriver().reset();

    auto dma  = makeDma("post-stop-reject");
    auto pool = rogue_test::makePool();
    auto tx   = rogue_test::makeFrame(pool, {1, 2, 3, 4});

    dma->stop();

    CHECK_THROWS_AS(dma->acceptReq(64, false), rogue::GeneralError);
    CHECK_THROWS_AS(dma->acceptReq(64, true), rogue::GeneralError);
    CHECK_THROWS_AS(dma->acceptFrame(tx), rogue::GeneralError);
    CHECK_EQ(dma->getBuffSize(), 0U);

    dma.reset();
}

TEST_CASE("AxiStreamDma stop waits for an in-flight driver getter") {
    fakeDriver().reset();

    auto dma = makeDma("getter-race");

    uint32_t value = 0;
    checkStopWaitsForBlockedDriverCall(dma, ROGUE_FAKE_AXI_DMA_BLOCK_IOCTL_BUFF_SIZE, [&] {
        value = dma->getBuffSize();
    });

    CHECK_EQ(value, 4096U);
    dma.reset();
}

TEST_CASE("AxiStreamDma stop waits for in-flight zero-copy allocation and return") {
    fakeDriver().reset();

    auto dma = makeDma("alloc-return-race");

    ris::FramePtr frame;
    checkStopWaitsForBlockedDriverCall(dma, ROGUE_FAKE_AXI_DMA_BLOCK_IOCTL_GET_INDEX, [&] {
        frame = dma->acceptReq(64, true);
    });

    REQUIRE(frame);
    REQUIRE_EQ(frame->bufferCount(), 1U);
    frame->clear();
    frame.reset();

    // Build a fresh instance so the retBuffer path can race stop() while fd_
    // is still open; the allocation half above has already stopped its DMA.
    dma.reset();
    fakeDriver().reset();
    dma   = makeDma("ret-buffer-race");
    frame = dma->acceptReq(64, true);
    REQUIRE(frame);

    checkStopWaitsForBlockedDriverCall(dma, ROGUE_FAKE_AXI_DMA_BLOCK_IOCTL_RET_INDEX, [&] {
        frame->clear();
    });

    CHECK_EQ(fakeDriver().retIndexCount(), 1U);
    dma.reset();
}

TEST_CASE("AxiStreamDma stop waits for an in-flight transmit write") {
#ifdef __APPLE__
    MESSAGE("Skipping write interposition check on macOS");
#else
    fakeDriver().reset();

    auto dma   = makeDma("write-race");
    auto pool  = rogue_test::makePool();
    auto frame = rogue_test::makeFrame(pool, std::vector<uint8_t>{0x10, 0x20, 0x30, 0x40});

    checkStopWaitsForBlockedDriverCall(dma, ROGUE_FAKE_AXI_DMA_BLOCK_WRITE, [&] {
        dma->acceptFrame(frame);
    });

    dma.reset();
#endif
}
