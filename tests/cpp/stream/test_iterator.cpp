#include <vector>

#include "doctest/doctest.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/FrameIterator.h"
#include "support/test_helpers.h"

TEST_CASE("Frame iterator traverses across buffer boundaries") {
    auto pool  = rogue_test::makePool(4, 0);
    auto frame = rogue_test::makeFrame(pool, {0, 1, 2, 3, 4, 5, 6, 7, 8, 9});

    auto iter = frame->begin();
    CHECK_EQ(iter.remBuffer(), 4U);
    CHECK_EQ(iter[0], 0U);
    CHECK_EQ(iter[5], 5U);

    auto firstBufferEnd = iter.endBuffer();
    CHECK_EQ(firstBufferEnd - iter, 4);

    iter += 4;
    CHECK_EQ(*iter, 4U);
    CHECK_EQ(iter.remBuffer(), 4U);
    CHECK_EQ(iter.endBuffer() - iter, 4);

    iter += 4;
    CHECK_EQ(*iter, 8U);
    CHECK_EQ(iter.remBuffer(), 2U);
    CHECK_EQ(frame->end() - iter, 2);
}

TEST_CASE("Frame iterator distinguishes readable payload from writable capacity") {
    auto pool  = rogue_test::makePool(4, 0);
    auto frame = pool->acceptReq(10, false);

    auto writer = frame->beginWrite();
    const std::vector<uint8_t> bytes = {10, 11, 12, 13, 14, 15};
    rogue::interfaces::stream::toFrame(writer, static_cast<uint32_t>(bytes.size()), const_cast<uint8_t*>(bytes.data()));
    frame->setPayload(static_cast<uint32_t>(bytes.size()));

    CHECK_EQ(frame->end() - frame->begin(), 6);
    CHECK_EQ(frame->endWrite() - frame->beginWrite(), 12);

    auto reader = frame->begin();
    CHECK_EQ(reader[5], 15U);
    CHECK_EQ(rogue_test::readFrame(frame, 6), bytes);
}

TEST_CASE("Frame iterator supports copy operations between disjoint frames") {
    auto pool      = rogue_test::makePool(4, 0);
    auto srcFrame  = rogue_test::makeFrame(pool, {1, 3, 5, 7, 9, 11, 13});
    auto dstFrame  = pool->acceptReq(7, false);
    auto srcIter   = srcFrame->begin();
    auto dstWriter = dstFrame->beginWrite();

    rogue::interfaces::stream::copyFrame(srcIter, 7, dstWriter);
    dstFrame->setPayload(7);

    CHECK_EQ(rogue_test::readFrame(dstFrame, 7), std::vector<uint8_t>({1, 3, 5, 7, 9, 11, 13}));
}
