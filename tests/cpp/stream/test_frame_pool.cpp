/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Native C++ tests for stream frame and pool primitives, covering fixed-size
 * pool allocation, multi-buffer frame construction, append semantics, and
 * payload/accounting helpers that enforce size and availability rules.
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
#include "rogue/GeneralError.h"
#include "rogue/interfaces/stream/Buffer.h"
#include "rogue/interfaces/stream/Frame.h"
#include "support/test_helpers.h"

TEST_CASE("Stream pool allocates fixed-size multi-buffer frames and returns buffers") {
    auto pool = rogue_test::makePool(4, 1);

    {
        auto frame = pool->acceptReq(10, false);
        CHECK_EQ(frame->bufferCount(), 3U);
        CHECK_EQ(frame->getSize(), 12U);
        CHECK_EQ(pool->getAllocCount(), 3U);
        CHECK_EQ(pool->getAllocBytes(), 12U);
    }

    CHECK_EQ(pool->getAllocCount(), 0U);
    CHECK_EQ(pool->getAllocBytes(), 0U);
}

TEST_CASE("Frame payload accounting and append operations stay consistent") {
    auto pool   = rogue_test::makePool(4, 0);
    auto frameA = rogue_test::makeFrame(pool, {1, 2, 3, 4});
    auto frameB = rogue_test::makeFrame(pool, {5, 6, 7, 8, 9});

    CHECK_EQ(frameA->getPayload(), 4U);
    CHECK_EQ(frameB->getPayload(), 5U);
    CHECK_EQ(frameB->bufferCount(), 2U);

    frameA->appendFrame(frameB);

    CHECK_EQ(frameA->bufferCount(), 3U);
    CHECK_EQ(frameA->getPayload(), 9U);
    CHECK(frameB->isEmpty());
    CHECK_EQ(frameB->getPayload(), 0U);
    CHECK_EQ(rogue_test::readFrame(frameA, 9), std::vector<uint8_t>({1, 2, 3, 4, 5, 6, 7, 8, 9}));
}

TEST_CASE("Frame payload helpers enforce bounds and minimums") {
    auto pool  = rogue_test::makePool(4, 0);
    auto frame = pool->acceptReq(8, false);

    CHECK_EQ(frame->getPayload(), 0U);
    CHECK_EQ(frame->getAvailable(), 8U);

    frame->setPayload(6);
    CHECK_EQ(frame->getPayload(), 6U);
    CHECK_EQ(frame->getAvailable(), 2U);

    frame->minPayload(4);
    CHECK_EQ(frame->getPayload(), 6U);

    frame->minPayload(7);
    CHECK_EQ(frame->getPayload(), 7U);

    frame->adjustPayload(-3);
    CHECK_EQ(frame->getPayload(), 4U);

    CHECK_THROWS_AS(frame->setPayload(9), rogue::GeneralError);

    frame->setPayloadFull();
    CHECK_EQ(frame->getPayload(), 8U);

    frame->setPayloadEmpty();
    CHECK_EQ(frame->getPayload(), 0U);
}
