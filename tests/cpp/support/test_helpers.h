/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Shared helper utilities for the native C++ Rogue tests, including stream
 * pool/frame construction helpers, frame read/write convenience functions, and
 * a small polling helper for asynchronous test assertions.
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
#ifndef ROGUE_TEST_CPP_SUPPORT_TEST_HELPERS_H
#define ROGUE_TEST_CPP_SUPPORT_TEST_HELPERS_H

#include <stdint.h>

#include <chrono>
#include <functional>
#include <memory>
#include <thread>
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

inline bool waitUntil(const std::function<bool()>& predicate, uint32_t timeoutMs = 250) {
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(timeoutMs);
    while (std::chrono::steady_clock::now() < deadline) {
        if (predicate()) return true;
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
    return predicate();
}

}  // namespace rogue_test

#endif
