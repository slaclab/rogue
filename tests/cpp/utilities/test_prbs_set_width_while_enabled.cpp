/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression test for utilities::Prbs::runThread(). enable(size) validates
 * the frame size once against byteWidth_/minSize_, but setWidth() can change
 * both while the generator thread is running. genFrame() re-validates and
 * throws rogue::GeneralError; before the fix that throw escaped runThread()
 * and the process died via std::terminate(). The thread must instead log,
 * clear threadEn_, and exit so disable() can join it.
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
#include <memory>
#include <thread>

#include "doctest/doctest.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/utilities/Prbs.h"

namespace ris = rogue::interfaces::stream;
namespace ru  = rogue::utilities;

namespace {

class CountingSink : public ris::Slave {
  public:
    CountingSink() : ris::Slave() {}

    void acceptFrame(ris::FramePtr frame) override {
        count.fetch_add(1, std::memory_order_relaxed);
    }

    std::atomic<uint32_t> count{0};
};

bool waitFor(const std::atomic<uint32_t>& value, uint32_t target, std::chrono::seconds timeout) {
    const auto deadline = std::chrono::steady_clock::now() + timeout;
    while (value.load() < target) {
        if (std::chrono::steady_clock::now() >= deadline) return false;
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
    return true;
}

}  // namespace

TEST_CASE("Prbs setWidth() after enable() stops the TX thread instead of aborting") {
    std::shared_ptr<ru::Prbs> tx  = ru::Prbs::create();
    std::shared_ptr<CountingSink> rx = std::make_shared<CountingSink>();
    tx->addSlave(rx);

    tx->setWidth(32);
    tx->enable(12);
    REQUIRE(waitFor(rx->count, 1, std::chrono::seconds(5)));

    // 12 bytes is neither a multiple of the new 16-byte width nor >= minSize_,
    // so the next genFrame(txSize_) in runThread() throws.
    tx->setWidth(128);

    // Give the generator a chance to hit the invalid size. Without the catch
    // in runThread() this is where the process would std::terminate().
    std::this_thread::sleep_for(std::chrono::milliseconds(50));

    tx->disable();

    // Object remains usable with a size valid for the new width.
    const uint32_t before = rx->count.load();
    tx->genFrame(128);
    CHECK(waitFor(rx->count, before + 1, std::chrono::seconds(5)));
}
