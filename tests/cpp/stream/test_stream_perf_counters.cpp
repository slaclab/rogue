/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Behavioural coverage for the stream-path performance counters: Pool's
 * monotonic allocation totals and peak, Frame's construction count, FrameLock
 * acquisitions, and the buffer-copy count/bytes incremented inside the
 * FrameIterator.h copy helpers.
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
#include <vector>

#include "doctest/doctest.h"
#include "rogue/PerfCounters.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/FrameIterator.h"
#include "rogue/interfaces/stream/FrameLock.h"
#include "rogue/interfaces/stream/Pool.h"
#include "support/test_helpers.h"

TEST_CASE("Pool allocation totals raise by the allocated count and bytes, never decrementing on free") {
    auto pool = rogue_test::makePool(4, 0);

    {
        auto frame = pool->acceptReq(10, false);
        CHECK_EQ(frame->bufferCount(), 3U);
        CHECK_EQ(pool->getAllocCount(), 3U);
        CHECK_EQ(pool->getAllocBytes(), 12U);
        CHECK_EQ(pool->getAllocTotalCount(), 3U);
        CHECK_EQ(pool->getAllocTotalBytes(), 12U);
    }

    // Buffers are freed here (frame went out of scope). The live gauges
    // return toward zero, but the monotonic totals must not move.
    CHECK_EQ(pool->getAllocCount(), 0U);
    CHECK_EQ(pool->getAllocBytes(), 0U);
    CHECK_EQ(pool->getAllocTotalCount(), 3U);
    CHECK_EQ(pool->getAllocTotalBytes(), 12U);
}

TEST_CASE("Pool peak allocated bytes reports the historical maximum, not the final live total") {
    auto pool = rogue_test::makePool(4, 0);

    CHECK_EQ(pool->getAllocPeakBytes(), 0U);

    {
        auto bigFrame = pool->acceptReq(20, false);  // 5 buffers * 4 bytes = 20 live bytes
        CHECK_EQ(pool->getAllocBytes(), 20U);
    }

    // bigFrame freed: live bytes return to zero, but the peak must remain.
    CHECK_EQ(pool->getAllocBytes(), 0U);
    CHECK_EQ(pool->getAllocPeakBytes(), 20U);

    {
        auto smallFrame = pool->acceptReq(4, false);  // 1 buffer * 4 bytes = 4 live bytes
        CHECK_EQ(pool->getAllocBytes(), 4U);
    }

    // The peak still reports the first, larger maximum, not the smaller
    // second allocation or the zero the pool returned to in between.
    CHECK_EQ(pool->getAllocPeakBytes(), 20U);
}

TEST_CASE("Frame::create raises the process-wide frame construction count by exactly one per call") {
    uint64_t before = rogue::PerfCounters::getFrameCreateCount();

    auto frame1 = rogue::interfaces::stream::Frame::create();
    CHECK_EQ(rogue::PerfCounters::getFrameCreateCount() - before, 1U);

    auto frame2 = rogue::interfaces::stream::Frame::create();
    CHECK_EQ(rogue::PerfCounters::getFrameCreateCount() - before, 2U);
}

TEST_CASE("FrameLock counts the RAII construction path, a redundant lock, and an explicit re-lock") {
    auto pool  = rogue_test::makePool(4, 0);
    auto frame = pool->acceptReq(4, false);

    uint64_t before = rogue::PerfCounters::getFrameLockCount();

    // The ordinary usage path: FrameLock::create() never calls lock(), so
    // the constructor's direct lock must be counted on its own.
    auto frameLock = rogue::interfaces::stream::FrameLock::create(frame);
    CHECK_EQ(rogue::PerfCounters::getFrameLockCount() - before, 1U);

    // A redundant lock() while already locked must add nothing: this proves
    // the guarded branch is actually guarded rather than assumed.
    frameLock->lock();
    CHECK_EQ(rogue::PerfCounters::getFrameLockCount() - before, 1U);

    // An explicit unlock() followed by lock() takes the guarded branch's
    // real lock path and must add exactly one more.
    frameLock->unlock();
    frameLock->lock();
    CHECK_EQ(rogue::PerfCounters::getFrameLockCount() - before, 2U);
}

TEST_CASE("toFrame counts one buffer copy per executed memcpy and the exact bytes moved") {
    auto pool = rogue_test::makePool(4, 0);
    const std::vector<uint8_t> bytes = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9};

    uint64_t countBefore = rogue::PerfCounters::getBufferCopyCount();
    uint64_t bytesBefore = rogue::PerfCounters::getBufferCopyBytes();

    // makeFrame() allocates a 3-buffer (4, 4, 2 byte) frame and writes
    // through toFrame(), whose definition lives in FrameIterator.h and is
    // compiled into this NO_PYTHON test translation unit. The counter it
    // increments is defined once in the separately-compiled
    // rogue-core-shared library, so this assertion also proves the counter
    // did not fragment into a private per-translation-unit copy.
    auto frame = rogue_test::makeFrame(pool, bytes);
    CHECK_EQ(frame->bufferCount(), 3U);

    CHECK_EQ(rogue::PerfCounters::getBufferCopyCount() - countBefore, 3U);
    CHECK_EQ(rogue::PerfCounters::getBufferCopyBytes() - bytesBefore, 10U);
}

TEST_CASE("fromFrame counts one buffer copy per executed memcpy and the exact bytes moved") {
    auto pool = rogue_test::makePool(4, 0);
    const std::vector<uint8_t> bytes = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9};
    auto frame                       = rogue_test::makeFrame(pool, bytes);

    uint64_t countBefore = rogue::PerfCounters::getBufferCopyCount();
    uint64_t bytesBefore = rogue::PerfCounters::getBufferCopyBytes();

    auto readBack = rogue_test::readFrame(frame, static_cast<uint32_t>(bytes.size()));

    CHECK_EQ(readBack, bytes);
    CHECK_EQ(rogue::PerfCounters::getBufferCopyCount() - countBefore, 3U);
    CHECK_EQ(rogue::PerfCounters::getBufferCopyBytes() - bytesBefore, 10U);
}

TEST_CASE("copyFrame counts one buffer copy per executed memcpy and the exact bytes moved") {
    auto pool = rogue_test::makePool(4, 0);
    const std::vector<uint8_t> bytes = {1, 3, 5, 7, 9, 11, 13, 15, 17, 19};

    auto srcFrame = rogue_test::makeFrame(pool, bytes);
    auto dstFrame = pool->acceptReq(static_cast<uint32_t>(bytes.size()), false);
    auto srcIter  = srcFrame->begin();
    auto dstIter  = dstFrame->beginWrite();

    uint64_t countBefore = rogue::PerfCounters::getBufferCopyCount();
    uint64_t bytesBefore = rogue::PerfCounters::getBufferCopyBytes();

    rogue::interfaces::stream::copyFrame(srcIter, static_cast<uint32_t>(bytes.size()), dstIter);
    dstFrame->setPayload(static_cast<uint32_t>(bytes.size()));

    // Check the copyFrame deltas before calling readFrame() below, which
    // itself exercises fromFrame() and would otherwise add its own copies.
    CHECK_EQ(rogue::PerfCounters::getBufferCopyCount() - countBefore, 3U);
    CHECK_EQ(rogue::PerfCounters::getBufferCopyBytes() - bytesBefore, 10U);
    CHECK_EQ(rogue_test::readFrame(dstFrame, static_cast<uint32_t>(bytes.size())), bytes);
}
