/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression test for stream::TcpCore receiving frames before the bridge is
 * owned by a std::shared_ptr.
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
#include <unistd.h>

#include <atomic>
#include <chrono>
#include <memory>
#include <string>
#include <thread>

#include "doctest/doctest.h"
#include "rogue/GeneralError.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/interfaces/stream/TcpClient.h"
#include "rogue/interfaces/stream/TcpServer.h"
#include "support/test_helpers.h"

namespace ris = rogue::interfaces::stream;

namespace {

struct ServerWithPort {
    ris::TcpServerPtr server;
    uint16_t port;
};

ServerWithPort createServerOnAvailablePort() {
    const uint16_t start = static_cast<uint16_t>(20000 + ((getpid() % 200) * 128));

    for (uint32_t offset = 0; offset < 128; offset += 2) {
        const uint16_t port = static_cast<uint16_t>(start + offset);
        try {
            return {ris::TcpServer::create("127.0.0.1", port), port};
        } catch (const rogue::GeneralError&) {
            continue;
        }
    }

    FAIL("Could not create stream::TcpServer on an available TCP port pair");
    return {nullptr, 0};
}

}  // namespace

TEST_CASE("TcpClient accepts frames that arrive before a shared_ptr owns it") {
    auto serverWithPort = createServerOnAvailablePort();
    auto server         = serverWithPort.server;
    auto master         = ris::Master::create();
    auto pool           = rogue_test::makePool();
    auto slave          = ris::Slave::create();
    master->addSlave(server);

    // std::make_shared and Boost.Python both construct the bridge before the
    // owning shared_ptr exists, while the receive thread is already running.
    // A plain new keeps that window open for the whole test instead of a few
    // microseconds.
    ris::TcpClient* raw = new ris::TcpClient("127.0.0.1", serverWithPort.port);
    raw->addSlave(slave);

    std::atomic<bool> feed{true};
    std::thread feeder([&]() {
        while (feed.load()) {
            master->sendFrame(rogue_test::makeFrame(pool, {0x01, 0x02, 0x03, 0x04}));
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
    });

    const bool beforeOwned = rogue_test::waitUntil([&]() { return slave->getFrameCount() > 0; }, 2000);

    ris::TcpClientPtr client(raw);
    const uint64_t ownedAt = slave->getFrameCount();
    const bool afterOwned  = rogue_test::waitUntil([&]() { return slave->getFrameCount() > ownedAt; }, 2000);

    feed.store(false);
    feeder.join();
    client->stop();
    server->stop();

    CHECK(beforeOwned);
    CHECK(afterOwned);
    CHECK(slave->getByteCount() == 4 * slave->getFrameCount());
}
