#ifndef ROGUE_TEST_CPP_SUPPORT_TEST_HELPERS_H
#define ROGUE_TEST_CPP_SUPPORT_TEST_HELPERS_H

#include <stdint.h>

#include <memory>
#include <vector>

#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/FrameIterator.h"
#include "rogue/interfaces/stream/Pool.h"

namespace rogue_test {

inline std::shared_ptr<rogue::interfaces::stream::Pool> makePool(uint32_t fixedSize = 0, uint32_t poolSize = 0) {
    auto pool = std::make_shared<rogue::interfaces::stream::Pool>();
    if (fixedSize != 0) pool->setFixedSize(fixedSize);
    if (poolSize != 0) pool->setPoolSize(poolSize);
    return pool;
}

inline std::vector<uint8_t> readFrame(const std::shared_ptr<rogue::interfaces::stream::Frame>& frame, uint32_t count) {
    std::vector<uint8_t> bytes(count);
    auto iter = frame->begin();
    rogue::interfaces::stream::fromFrame(iter, count, bytes.data());
    return bytes;
}

inline void writeFrame(const std::shared_ptr<rogue::interfaces::stream::Frame>& frame, const std::vector<uint8_t>& data) {
    auto iter = frame->beginWrite();
    rogue::interfaces::stream::toFrame(iter, static_cast<uint32_t>(data.size()), const_cast<uint8_t*>(data.data()));
    frame->setPayload(static_cast<uint32_t>(data.size()));
}

inline std::shared_ptr<rogue::interfaces::stream::Frame> makeFrame(
    const std::shared_ptr<rogue::interfaces::stream::Pool>& pool,
    const std::vector<uint8_t>& bytes) {
    auto frame = pool->acceptReq(static_cast<uint32_t>(bytes.size()), false);
    writeFrame(frame, bytes);
    return frame;
}

}  // namespace rogue_test

#endif
