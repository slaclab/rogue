/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression test for AxiStreamDma receiving data before it is owned by a
 * std::shared_ptr, using the fake_dma_preload LD_PRELOAD backend.
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

#include <chrono>
#include <memory>
#include <thread>

#include "doctest/doctest.h"
#include "rogue/hardware/axi/AxiStreamDma.h"
#include "rogue/interfaces/stream/Slave.h"
#include "support/fake_dma_hooks.h"

namespace rha = rogue::hardware::axi;
namespace ris = rogue::interfaces::stream;

namespace {

constexpr int kQueuedRx = 3;

bool waitUntilFrames(const ris::SlavePtr& slave, uint64_t count, uint32_t timeoutMs) {
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(timeoutMs);
    while (std::chrono::steady_clock::now() < deadline) {
        if (slave->getFrameCount() >= count) return true;
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
    return slave->getFrameCount() >= count;
}

}  // namespace

// std::make_shared and Boost.Python both construct AxiStreamDma before the
// owning shared_ptr exists, while the receive thread is already running. Data
// already queued in the driver makes the worker create a zero-copy buffer from
// the inherited Pool, which needs shared_from_this(). A plain new keeps that
// window open instead of a few microseconds. Frames must wait in the driver
// until the object is owned rather than terminating the process.
TEST_CASE("AxiStreamDma receives data queued before a shared_ptr owns it") {
    auto& fake = rogue_test::fakeDma();
    REQUIRE(fake.isClean());
    fake.reset();
    fake.queueRx(kQueuedRx);

    rha::AxiStreamDma* raw = new rha::AxiStreamDma(fake.path(), 0, false);
    auto slave             = ris::Slave::create();
    raw->addSlave(slave);

    std::this_thread::sleep_for(std::chrono::milliseconds(200));
    const uint64_t whileUnowned = slave->getFrameCount();

    rha::AxiStreamDmaPtr dma(raw);
    const bool afterOwned = waitUntilFrames(slave, kQueuedRx, 2000);

    dma->stop();
    dma.reset();

    CHECK_EQ(whileUnowned, 0);
    CHECK(afterOwned);
    CHECK_EQ(slave->getByteCount(), 4 * slave->getFrameCount());
    CHECK_EQ(fake.retIndexCount(), kQueuedRx);
    CHECK(fake.isClean());
}

// An AxiStreamDma destroyed before it is ever owned must still stop its
// receive thread, which is waiting for ownership rather than receiving.
TEST_CASE("AxiStreamDma stops before a shared_ptr owns it") {
    auto& fake = rogue_test::fakeDma();
    REQUIRE(fake.isClean());
    fake.reset();
    fake.queueRx(1);

    rha::AxiStreamDma* raw = new rha::AxiStreamDma(fake.path(), 0, false);
    std::this_thread::sleep_for(std::chrono::milliseconds(50));

    const auto start = std::chrono::steady_clock::now();
    delete raw;
    const auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - start);

    CHECK_LT(elapsed.count(), 2000);
    CHECK(fake.isClean());
    fake.reset();
}
