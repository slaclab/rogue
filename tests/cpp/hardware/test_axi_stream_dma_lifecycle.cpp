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
#include <stdint.h>

#include <atomic>
#include <chrono>
#include <exception>
#include <functional>
#include <memory>
#include <thread>
#include <vector>

#include "doctest/doctest.h"
#include "rogue/GeneralError.h"
#include "rogue/hardware/axi/AxiStreamDma.h"
#include "rogue/interfaces/stream/Frame.h"
#include "support/fake_dma_hooks.h"
#include "support/test_helpers.h"

namespace rha = rogue::hardware::axi;
namespace ris = rogue::interfaces::stream;

namespace {

void requireFakeDmaClean() {
    auto& fake = rogue_test::fakeDma();
    INFO("fd_count=" << fake.fdCount());
    INFO("region_count=" << fake.regionCount());
    INFO("active_calls=" << fake.activeCallCount());
    INFO("overflow_count=" << fake.overflowCount());
    REQUIRE(fake.isClean());
    REQUIRE_EQ(fake.mappedCount(), 0);
}

void checkFakeDmaClean() {
    auto& fake = rogue_test::fakeDma();
    INFO("fd_count=" << fake.fdCount());
    INFO("region_count=" << fake.regionCount());
    INFO("active_calls=" << fake.activeCallCount());
    INFO("overflow_count=" << fake.overflowCount());
    CHECK(fake.isClean());
    CHECK_EQ(fake.mappedCount(), 0);
}

rha::AxiStreamDmaPtr makeDma() {
    return rha::AxiStreamDma::create(rogue_test::fakeDma().path(), 0, false);
}

void checkStopWaitsForBlockedDriverCall(const rha::AxiStreamDmaPtr& dma,
                                        rogue_test::FakeDmaBlockOp blockOp,
                                        const std::function<void()>& call) {
    rogue_test::fakeDma().blockNext(blockOp);

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

    const bool blocked = rogue_test::fakeDma().waitBlocked(1000);
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
    CHECK_FALSE(rogue_test::fakeDma().closeDuringDriverCall());

    rogue_test::fakeDma().releaseBlocked();

    caller.join();
    stopper.join();
    if (callError) std::rethrow_exception(callError);

    CHECK(callDone.load());
    CHECK(stopDone.load());
    CHECK_FALSE(rogue_test::fakeDma().closeDuringDriverCall());
}

}  // namespace

TEST_CASE("AxiStreamDma rejects new stream work after stop while retaining shared descriptor") {
    requireFakeDmaClean();
    rogue_test::fakeDma().reset();

    auto dma  = makeDma();
    auto pool = rogue_test::makePool();
    auto tx   = rogue_test::makeFrame(pool, {1, 2, 3, 4});

    dma->stop();

    CHECK_THROWS_AS(dma->acceptReq(64, false), rogue::GeneralError);
    CHECK_THROWS_AS(dma->acceptReq(64, true), rogue::GeneralError);
    CHECK_THROWS_AS(dma->acceptFrame(tx), rogue::GeneralError);
    CHECK_EQ(dma->getBuffSize(), 0U);

    dma.reset();
    checkFakeDmaClean();
}

TEST_CASE("AxiStreamDma stop waits for an in-flight driver getter") {
    requireFakeDmaClean();
    rogue_test::fakeDma().reset();

    auto dma = makeDma();

    uint32_t value = 0;
    checkStopWaitsForBlockedDriverCall(dma, rogue_test::FakeDmaBlockBuffSize, [&] {
        value = dma->getBuffSize();
    });

    CHECK_EQ(value, 4096U);
    dma.reset();
    checkFakeDmaClean();
}

TEST_CASE("AxiStreamDma stop waits for in-flight zero-copy allocation and return") {
    requireFakeDmaClean();
    rogue_test::fakeDma().reset();

    auto dma = makeDma();

    ris::FramePtr frame;
    checkStopWaitsForBlockedDriverCall(dma, rogue_test::FakeDmaBlockGetIndex, [&] {
        frame = dma->acceptReq(64, true);
    });

    REQUIRE(static_cast<bool>(frame));
    REQUIRE_EQ(frame->bufferCount(), 1U);
    frame->clear();
    frame.reset();
    dma.reset();
    checkFakeDmaClean();

    rogue_test::fakeDma().reset();
    dma   = makeDma();
    frame = dma->acceptReq(64, true);
    REQUIRE(static_cast<bool>(frame));

    checkStopWaitsForBlockedDriverCall(dma, rogue_test::FakeDmaBlockRetIndex, [&] {
        frame->clear();
    });

    CHECK_EQ(rogue_test::fakeDma().retIndexCount(), 1);
    frame.reset();
    dma.reset();
    checkFakeDmaClean();
}

TEST_CASE("AxiStreamDma stop waits for an in-flight transmit write") {
    requireFakeDmaClean();
    rogue_test::fakeDma().reset();

    auto dma   = makeDma();
    auto pool  = rogue_test::makePool();
    auto frame = rogue_test::makeFrame(pool, std::vector<uint8_t>{0x10, 0x20, 0x30, 0x40});

    checkStopWaitsForBlockedDriverCall(dma, rogue_test::FakeDmaBlockWrite, [&] {
        dma->acceptFrame(frame);
    });

    dma.reset();
    checkFakeDmaClean();
}
