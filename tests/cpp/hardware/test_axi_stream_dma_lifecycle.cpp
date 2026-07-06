/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Native C++ lifecycle tests for AxiStreamDma stop/fd races using the
 * fake_dma_preload LD_PRELOAD backend.
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
#include <dlfcn.h>
#include <stdint.h>

#include <atomic>
#include <chrono>
#include <exception>
#include <functional>
#include <memory>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

#include "doctest/doctest.h"
#include "rogue/GeneralError.h"
#include "rogue/hardware/axi/AxiStreamDma.h"
#include "rogue/interfaces/stream/Frame.h"
#include "support/test_helpers.h"

namespace rha = rogue::hardware::axi;
namespace ris = rogue::interfaces::stream;

namespace {

enum FakeDmaBlockOp {
    FakeDmaBlockNone     = 0,
    FakeDmaBlockGetIndex = 1,
    FakeDmaBlockRetIndex = 2,
    FakeDmaBlockBuffSize = 3,
    FakeDmaBlockWrite    = 4,
};

class FakeDma {
  public:
    using PathFn            = const char* (*)();
    using ResetFn           = void (*)();
    using BlockNextFn       = void (*)(int);
    using WaitBlockedFn     = int (*)(uint32_t);
    using ReleaseBlockedFn  = void (*)();
    using CountFn           = int (*)();

    FakeDma() {
        path_              = load<PathFn>("fakedma_path");
        reset_             = load<ResetFn>("fakedma_reset");
        blockNext_         = load<BlockNextFn>("fakedma_block_next");
        waitBlocked_       = load<WaitBlockedFn>("fakedma_wait_blocked");
        releaseBlocked_    = load<ReleaseBlockedFn>("fakedma_release_blocked");
        mappedCount_       = load<CountFn>("fakedma_mapped_count");
        retIndexCount_     = load<CountFn>("fakedma_ret_index_count");
        closeDuringCall_   = load<CountFn>("fakedma_close_during_driver_call");
    }

    const char* path() const { return path_(); }
    void reset() const { reset_(); }
    void blockNext(FakeDmaBlockOp op) const { blockNext_(static_cast<int>(op)); }
    bool waitBlocked(uint32_t timeoutMs) const { return waitBlocked_(timeoutMs) != 0; }
    void releaseBlocked() const { releaseBlocked_(); }
    int mappedCount() const { return mappedCount_(); }
    int retIndexCount() const { return retIndexCount_(); }
    bool closeDuringDriverCall() const { return closeDuringCall_() != 0; }

  private:
    template <typename Func>
    Func load(const char* name) {
        void* sym = dlsym(RTLD_DEFAULT, name);
        if (sym == nullptr) throw std::runtime_error(dlerror());
        return reinterpret_cast<Func>(sym);
    }

    PathFn path_;
    ResetFn reset_;
    BlockNextFn blockNext_;
    WaitBlockedFn waitBlocked_;
    ReleaseBlockedFn releaseBlocked_;
    CountFn mappedCount_;
    CountFn retIndexCount_;
    CountFn closeDuringCall_;
};

FakeDma& fakeDma() {
    static FakeDma fake;
    return fake;
}

rha::AxiStreamDmaPtr makeDma() {
    return rha::AxiStreamDma::create(fakeDma().path(), 0, false);
}

void checkStopWaitsForBlockedDriverCall(const rha::AxiStreamDmaPtr& dma,
                                        FakeDmaBlockOp blockOp,
                                        const std::function<void()>& call) {
    fakeDma().blockNext(blockOp);

    std::atomic<bool> callDone{false};
    std::exception_ptr callError;
    std::thread caller([&] {
        try {
            call();
            callDone.store(true);
        } catch (...) {
            callError = std::current_exception();
        }
    });

    const bool blocked = fakeDma().waitBlocked(1000);
    CHECK(blocked);
    if (!blocked) {
        if (caller.joinable()) caller.join();
        if (callError) std::rethrow_exception(callError);
        return;
    }
    CHECK_FALSE(callDone.load());

    std::atomic<bool> stopDone{false};
    std::thread stopper([&] {
        dma->stop();
        stopDone.store(true);
    });

    std::this_thread::sleep_for(std::chrono::milliseconds(25));
    CHECK_FALSE(stopDone.load());
    CHECK_FALSE(fakeDma().closeDuringDriverCall());

    fakeDma().releaseBlocked();

    caller.join();
    stopper.join();
    if (callError) std::rethrow_exception(callError);

    CHECK(callDone.load());
    CHECK(stopDone.load());
    CHECK_FALSE(fakeDma().closeDuringDriverCall());
}

}  // namespace

TEST_CASE("AxiStreamDma rejects new stream work after stop while retaining shared descriptor") {
    fakeDma().reset();
    REQUIRE_EQ(fakeDma().mappedCount(), 0);

    auto dma  = makeDma();
    auto pool = rogue_test::makePool();
    auto tx   = rogue_test::makeFrame(pool, {1, 2, 3, 4});

    dma->stop();

    CHECK_THROWS_AS(dma->acceptReq(64, false), rogue::GeneralError);
    CHECK_THROWS_AS(dma->acceptReq(64, true), rogue::GeneralError);
    CHECK_THROWS_AS(dma->acceptFrame(tx), rogue::GeneralError);
    CHECK_EQ(dma->getBuffSize(), 0U);

    dma.reset();
    CHECK_EQ(fakeDma().mappedCount(), 0);
}

TEST_CASE("AxiStreamDma stop waits for an in-flight driver getter") {
    fakeDma().reset();
    REQUIRE_EQ(fakeDma().mappedCount(), 0);

    auto dma = makeDma();

    uint32_t value = 0;
    checkStopWaitsForBlockedDriverCall(dma, FakeDmaBlockBuffSize, [&] {
        value = dma->getBuffSize();
    });

    CHECK_EQ(value, 4096U);
    dma.reset();
    CHECK_EQ(fakeDma().mappedCount(), 0);
}

TEST_CASE("AxiStreamDma stop waits for in-flight zero-copy allocation and return") {
    fakeDma().reset();
    REQUIRE_EQ(fakeDma().mappedCount(), 0);

    auto dma = makeDma();

    ris::FramePtr frame;
    checkStopWaitsForBlockedDriverCall(dma, FakeDmaBlockGetIndex, [&] {
        frame = dma->acceptReq(64, true);
    });

    REQUIRE(static_cast<bool>(frame));
    REQUIRE_EQ(frame->bufferCount(), 1U);
    frame->clear();
    frame.reset();
    dma.reset();
    CHECK_EQ(fakeDma().mappedCount(), 0);

    fakeDma().reset();
    dma   = makeDma();
    frame = dma->acceptReq(64, true);
    REQUIRE(static_cast<bool>(frame));

    checkStopWaitsForBlockedDriverCall(dma, FakeDmaBlockRetIndex, [&] {
        frame->clear();
    });

    CHECK_EQ(fakeDma().retIndexCount(), 1);
    frame.reset();
    dma.reset();
    CHECK_EQ(fakeDma().mappedCount(), 0);
}

TEST_CASE("AxiStreamDma stop waits for an in-flight transmit write") {
    fakeDma().reset();
    REQUIRE_EQ(fakeDma().mappedCount(), 0);

    auto dma   = makeDma();
    auto pool  = rogue_test::makePool();
    auto frame = rogue_test::makeFrame(pool, std::vector<uint8_t>{0x10, 0x20, 0x30, 0x40});

    checkStopWaitsForBlockedDriverCall(dma, FakeDmaBlockWrite, [&] {
        dma->acceptFrame(frame);
    });

    dma.reset();
    CHECK_EQ(fakeDma().mappedCount(), 0);
}
