/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Native C++ lifecycle test for deferred AxiStreamDma zero-copy buffer
 * returns overlapping stop(), using the fake_dma_preload LD_PRELOAD backend.
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
#include <condition_variable>
#include <exception>
#include <mutex>
#include <thread>

#include "doctest/doctest.h"
#include "rogue/hardware/axi/AxiStreamDma.h"
#include "rogue/interfaces/stream/Frame.h"
#include "support/fake_dma_hooks.h"

namespace rha = rogue::hardware::axi;

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

}  // namespace

TEST_CASE("AxiStreamDma stop waits for an in-flight zero-copy buffer return") {
    requireFakeDmaClean();
    auto& fake = rogue_test::fakeDma();
    fake.reset();

    auto dma   = rha::AxiStreamDma::create(fake.path(), 0, false);
    auto frame = dma->acceptReq(64, true);
    REQUIRE(static_cast<bool>(frame));
    REQUIRE_EQ(frame->bufferCount(), 1U);

    fake.blockNextRetIndex();

    std::atomic<bool> returnDone{false};
    std::exception_ptr returnError;
    std::thread returner([&] {
        try {
            frame->clear();
            returnDone.store(true);
        } catch (...) {
            returnError = std::current_exception();
        }
    });

    const bool blocked = fake.waitBlocked(1000);
    CHECK(blocked);
    if (!blocked) {
        fake.releaseBlocked();
        returner.join();
        if (returnError) std::rethrow_exception(returnError);
        return;
    }
    CHECK_FALSE(returnDone.load());

    std::mutex stopStateMtx;
    std::condition_variable stopStateCv;
    bool stopStarted = false;
    bool stopDone    = false;
    std::thread stopper([&] {
        {
            std::lock_guard<std::mutex> lock(stopStateMtx);
            stopStarted = true;
        }
        stopStateCv.notify_all();

        dma->stop();

        {
            std::lock_guard<std::mutex> lock(stopStateMtx);
            stopDone = true;
        }
        stopStateCv.notify_all();
    });

    bool started;
    bool completedWhileReturnBlocked;
    {
        std::unique_lock<std::mutex> lock(stopStateMtx);
        started = stopStateCv.wait_for(lock, std::chrono::seconds(1), [&] { return stopStarted; });
        completedWhileReturnBlocked =
            started && stopStateCv.wait_for(lock, std::chrono::milliseconds(25), [&] { return stopDone; });
    }

    CHECK(started);
    CHECK_FALSE(completedWhileReturnBlocked);
    CHECK_FALSE(fake.closeDuringDriverCall());

    fake.releaseBlocked();
    returner.join();
    stopper.join();
    if (returnError) std::rethrow_exception(returnError);

    CHECK(returnDone.load());
    CHECK(stopDone);
    CHECK_EQ(fake.retIndexCount(), 1);
    CHECK_FALSE(fake.closeDuringDriverCall());

    frame.reset();
    dma.reset();
    checkFakeDmaClean();
}
