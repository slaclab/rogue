/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Native C++ tests for core stream flow-control primitives, covering FIFO
 * trim/drop behavior under queue pressure, channel/error filtering rules, and
 * deterministic frame-count-based dropping in RateDrop.
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

#include <memory>
#include <condition_variable>
#include <mutex>
#include <vector>

#include "doctest/doctest.h"
#include "rogue/interfaces/stream/Fifo.h"
#include "rogue/interfaces/stream/Filter.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/RateDrop.h"
#include "support/test_helpers.h"

namespace ris = rogue::interfaces::stream;

namespace {

class RecordingSink : public ris::Slave {
  public:
    RecordingSink() : ris::Slave() {}

    void acceptFrame(ris::FramePtr frame) override {
        std::lock_guard<std::mutex> lock(mutex_);
        frames.push_back(frame);
    }

    std::size_t frameCount() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return frames.size();
    }

    ris::FramePtr frameAt(std::size_t index) const {
        std::lock_guard<std::mutex> lock(mutex_);
        return frames.at(index);
    }

  private:
    mutable std::mutex mutex_;

  public:
    std::vector<ris::FramePtr> frames;
};

class BlockingSink : public ris::Slave {
  public:
    BlockingSink() : ris::Slave(), released_(false), entered_(0) {}

    void acceptFrame(ris::FramePtr frame) override {
        std::unique_lock<std::mutex> lock(mutex_);
        frames.push_back(frame);
        ++entered_;
        condition_.notify_all();
        condition_.wait(lock, [&]() { return released_; });
    }

    std::size_t enteredCount() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return entered_;
    }

    std::size_t frameCount() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return frames.size();
    }

    ris::FramePtr frameAt(std::size_t index) const {
        std::lock_guard<std::mutex> lock(mutex_);
        return frames.at(index);
    }

    void releaseAll() {
        std::lock_guard<std::mutex> lock(mutex_);
        released_ = true;
        condition_.notify_all();
    }

  private:
    mutable std::mutex mutex_;
    std::condition_variable condition_;
    bool released_;
    std::size_t entered_;

  public:
    std::vector<ris::FramePtr> frames;
};

}  // namespace

TEST_CASE("Stream FIFO trims copied frames and drops when the queue is full") {
    auto pool = rogue_test::makePool(8, 0);
    auto fifo = ris::Fifo::create(1, 3, false);
    auto sink = std::make_shared<BlockingSink>();
    std::shared_ptr<ris::Slave> sinkBase = sink;

    fifo->addSlave(sinkBase);

    auto first  = rogue_test::makeFrame(pool, {1, 2, 3, 4, 5});
    auto second = rogue_test::makeFrame(pool, {6, 7, 8, 9});
    auto third  = rogue_test::makeFrame(pool, {10, 11, 12, 13});

    fifo->acceptFrame(first);
    REQUIRE_MESSAGE(rogue_test::waitUntil([&]() { return sink->enteredCount() == 1U; }, 2000),
                    "Timed out waiting for FIFO worker thread to enter the blocking sink");

    fifo->acceptFrame(second);
    fifo->acceptFrame(third);
    CHECK_EQ(fifo->dropCnt(), 1U);

    sink->releaseAll();
    REQUIRE_MESSAGE(rogue_test::waitUntil([&]() { return sink->frameCount() == 2U; }, 2000),
                    "Timed out waiting for FIFO worker thread to drain queued frames");

    CHECK_NE(sink->frameAt(0).get(), first.get());
    CHECK_EQ(sink->frameAt(0)->getPayload(), 3U);
    CHECK_EQ(rogue_test::readFrame(sink->frameAt(0), 3), std::vector<uint8_t>({1, 2, 3}));
    CHECK_EQ(sink->frameAt(1)->getPayload(), 3U);
    CHECK_EQ(rogue_test::readFrame(sink->frameAt(1), 3), std::vector<uint8_t>({6, 7, 8}));
}

TEST_CASE("Stream filter forwards only the configured channel and can drop errored frames") {
    auto pool   = rogue_test::makePool(8, 0);
    auto filter = ris::Filter::create(true, 3);
    auto sink   = std::make_shared<RecordingSink>();
    std::shared_ptr<ris::Slave> sinkBase = sink;

    filter->addSlave(sinkBase);

    auto wrongChannel = rogue_test::makeFrame(pool, {1});
    wrongChannel->setChannel(2);

    auto allowed = rogue_test::makeFrame(pool, {2, 3});
    allowed->setChannel(3);

    auto errored = rogue_test::makeFrame(pool, {4});
    errored->setChannel(3);
    errored->setError(1);

    filter->acceptFrame(wrongChannel);
    filter->acceptFrame(allowed);
    filter->acceptFrame(errored);

    REQUIRE_MESSAGE(rogue_test::waitUntil([&]() { return sink->frameCount() == 1U; }, 1000),
                    "Timed out waiting for the filter to forward the allowed frame");
    CHECK_EQ(sink->frameAt(0)->getChannel(), 3U);
    CHECK_EQ(sink->frameAt(0)->getError(), 0U);
    CHECK_EQ(rogue_test::readFrame(sink->frameAt(0), 2), std::vector<uint8_t>({2, 3}));
}

TEST_CASE("Stream rate drop in count mode keeps every N plus first frame") {
    auto pool      = rogue_test::makePool(8, 0);
    auto rateDrop  = ris::RateDrop::create(false, 2.0);
    auto sink      = std::make_shared<RecordingSink>();
    std::shared_ptr<ris::Slave> sinkBase = sink;

    rateDrop->addSlave(sinkBase);

    for (uint8_t idx = 0; idx < 5; ++idx) rateDrop->acceptFrame(rogue_test::makeFrame(pool, {idx}));

    REQUIRE_MESSAGE(rogue_test::waitUntil([&]() { return sink->frameCount() == 2U; }, 1000),
                    "Timed out waiting for RateDrop to forward the expected frames");
    CHECK_EQ(rogue_test::readFrame(sink->frameAt(0), 1), std::vector<uint8_t>({0}));
    CHECK_EQ(rogue_test::readFrame(sink->frameAt(1), 1), std::vector<uint8_t>({3}));
}
