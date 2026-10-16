/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression test for udp::Client and udp::Server receiving datagrams before
 * the bridge is owned by a std::shared_ptr.
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
#include <functional>
#include <memory>
#include <thread>

#include "doctest/doctest.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/protocols/udp/Client.h"
#include "rogue/protocols/udp/Server.h"
#include "support/test_helpers.h"

namespace ris = rogue::interfaces::stream;
namespace rpu = rogue::protocols::udp;

namespace {

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
// owning shared_ptr exists, while the receive thread is already running and
// requesting its first frame. Each case uses a plain new on the receiving
// side to keep that window open for the whole test instead of a few
// microseconds.

TEST_CASE("udp::Client accepts datagrams that arrive before a shared_ptr owns it") {
    auto server     = rpu::Server::create(0, false);
    auto serverSink = ris::Slave::create();
    auto master     = ris::Master::create();
    auto slave      = ris::Slave::create();
    master->addSlave(server);
    server->addSlave(serverSink);

    rpu::Client* raw = new rpu::Client("127.0.0.1", server->getPort(), false);
    raw->addSlave(slave);

    // The server only learns its peer address from the first datagram it
    // receives, so the unowned client has to speak first.
    auto pool = rogue_test::makePool();
    raw->acceptFrame(rogue_test::makeFrame(pool, {0xAA}));
    REQUIRE_MESSAGE(rogue_test::waitUntil([&]() { return serverSink->getFrameCount() > 0; }, 2000),
                    "Timed out waiting for the UDP server to receive the first datagram");

    rpu::ClientPtr client;
    const Delivery delivery = feedAcrossOwnership(master, slave, [&]() { client.reset(raw); });

    client->stop();
    server->stop();

    CHECK(delivery.beforeOwned);
    CHECK(delivery.afterOwned);
    CHECK(slave->getByteCount() == 4 * slave->getFrameCount());
}

TEST_CASE("udp::Server accepts datagrams that arrive before a shared_ptr owns it") {
    rpu::Server* raw = new rpu::Server(0, false);
    auto client      = rpu::Client::create("127.0.0.1", raw->getPort(), false);
    auto master      = ris::Master::create();
    auto slave       = ris::Slave::create();
    master->addSlave(client);
    raw->addSlave(slave);

    rpu::ServerPtr server;
    const Delivery delivery = feedAcrossOwnership(master, slave, [&]() { server.reset(raw); });

    client->stop();
    server->stop();

    CHECK(delivery.beforeOwned);
    CHECK(delivery.afterOwned);
    CHECK(slave->getByteCount() == 4 * slave->getFrameCount());
}

// The receive worker used to block in recvfrom() with nothing to wake it, so
// stop() only returned once the peer happened to send a datagram.
TEST_CASE("udp::Client and udp::Server stop without peer traffic") {
    auto server = rpu::Server::create(0, false);
    auto client = rpu::Client::create("127.0.0.1", server->getPort(), false);

    // Let both workers settle into their idle wait before stopping them.
    std::this_thread::sleep_for(std::chrono::milliseconds(50));

    const auto start = std::chrono::steady_clock::now();
    client->stop();
    server->stop();
    const auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - start);

    CHECK_LT(elapsed.count(), 2000);
}
