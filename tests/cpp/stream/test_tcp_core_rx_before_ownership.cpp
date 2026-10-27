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
#include <functional>
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

// Calls make() on successive TCP port pairs until a server binds; port receives the base port used.
template <typename Server>
Server bindOnAvailablePort(const std::function<Server(uint16_t)>& make, uint16_t* port) {
    const uint16_t start = static_cast<uint16_t>(20000 + ((getpid() % 200) * 128));

    for (uint32_t offset = 0; offset < 128; offset += 2) {
        *port = static_cast<uint16_t>(start + offset);
        try {
            return make(*port);
        } catch (const rogue::GeneralError&) {
            continue;
        }
    }

    FAIL("Could not create stream::TcpServer on an available TCP port pair");
    return Server();
}

struct Delivery {
    bool beforeOwned;
    bool afterOwned;
};

// Pushes frames through master while the receiving bridge is unowned, then
// runs own() to attach the shared_ptr and checks delivery continues.
Delivery feedAcrossOwnership(const ris::MasterPtr& master,
                             const ris::SlavePtr& slave,
                             const std::function<void()>& own) {
    auto pool = rogue_test::makePool();

    std::atomic<bool> feed{true};
    std::thread feeder([&]() {
        while (feed.load()) {
            master->sendFrame(rogue_test::makeFrame(pool, {0x01, 0x02, 0x03, 0x04}));
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
    });

    Delivery ret;
    ret.beforeOwned = rogue_test::waitUntil([&]() { return slave->getFrameCount() > 0; }, 2000);

    own();
    const uint64_t ownedAt = slave->getFrameCount();
    ret.afterOwned         = rogue_test::waitUntil([&]() { return slave->getFrameCount() > ownedAt; }, 2000);

    feed.store(false);
    feeder.join();
    return ret;
}

}  // namespace

// std::make_shared and Boost.Python both construct the bridge before the
// owning shared_ptr exists, while the receive thread is already running.
// Each case uses a plain new on the receiving side to keep that window open
// for the whole test instead of a few microseconds.

TEST_CASE("TcpClient accepts frames that arrive before a shared_ptr owns it") {
    uint16_t port = 0;
    auto server   = bindOnAvailablePort<ris::TcpServerPtr>(
        [](uint16_t p) { return ris::TcpServer::create("127.0.0.1", p); }, &port);
    auto master = ris::Master::create();
    auto slave  = ris::Slave::create();
    master->addSlave(server);

    ris::TcpClient* raw = new ris::TcpClient("127.0.0.1", port);
    raw->addSlave(slave);

    ris::TcpClientPtr client;
    const Delivery delivery = feedAcrossOwnership(master, slave, [&]() { client.reset(raw); });

    client->stop();
    server->stop();

    CHECK(delivery.beforeOwned);
    CHECK(delivery.afterOwned);
    CHECK(slave->getByteCount() == 4 * slave->getFrameCount());
}

TEST_CASE("TcpServer accepts frames that arrive before a shared_ptr owns it") {
    uint16_t port       = 0;
    ris::TcpServer* raw = bindOnAvailablePort<ris::TcpServer*>(
        [](uint16_t p) { return new ris::TcpServer("127.0.0.1", p); }, &port);
    auto client = ris::TcpClient::create("127.0.0.1", port);
    auto master = ris::Master::create();
    auto slave  = ris::Slave::create();
    master->addSlave(client);
    raw->addSlave(slave);

    ris::TcpServerPtr server;
    const Delivery delivery = feedAcrossOwnership(master, slave, [&]() { server.reset(raw); });

    client->stop();
    server->stop();

    CHECK(delivery.beforeOwned);
    CHECK(delivery.afterOwned);
    CHECK(slave->getByteCount() == 4 * slave->getFrameCount());
}
