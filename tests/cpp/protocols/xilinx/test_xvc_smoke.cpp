/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Native smoke coverage for Xvc start/stop event-driven shutdown.
 *
 * StartStopNoLeak is the baseline sanity case.  StopFastNoConn and
 * StopFastDuringRead assert the < 50 ms stop() latency budget that the
 * wakefd plumbing guarantees, with and without a connected client.
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
#include "rogue/Directives.h"

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <chrono>
#include <memory>
#include <thread>

#define NO_IMPORT_ARRAY
#include "doctest/doctest.h"
#include "rogue/protocols/xilinx/Xvc.h"

namespace rpx = rogue::protocols::xilinx;

namespace {

constexpr auto kMaxStopLatency = std::chrono::milliseconds(50);

}  // namespace

TEST_CASE("XvcSmoke.StartStopNoLeak") {
    // Baseline sanity — construct + destroy cycle must not leak or crash.
    // Use Xvc(0) so no TCP bind happens until start(); this case never starts,
    // so it just exercises ctor/dtor.
    {
        auto xvc = std::make_shared<rpx::Xvc>(0);
        (void)xvc;
    }
    CHECK(true);
}

TEST_CASE("XvcSmoke.StopFastNoConn") {
    // Xvc::stop() must return in < 50 ms with no client connected.
    // Xvc(0) + getPort() avoids the TOCTOU window of pre-binding port 0 in a
    // helper and then handing the port number to a separate Xvc bind.
    auto xvc = std::make_shared<rpx::Xvc>(0);
    xvc->start();
    // Let the server thread enter select()
    std::this_thread::sleep_for(std::chrono::milliseconds(10));

    auto t0      = std::chrono::steady_clock::now();
    xvc->stop();
    auto elapsed = std::chrono::steady_clock::now() - t0;
    auto ms      = std::chrono::duration_cast<std::chrono::milliseconds>(elapsed).count();

    INFO("Xvc::stop() latency: " << ms << " ms (budget " << kMaxStopLatency.count() << " ms)");
    CHECK(elapsed < kMaxStopLatency);
}

TEST_CASE("XvcSmoke.StopFastDuringRead") {
    // Xvc::stop() with an idle client connected must still return in < 50 ms
    // (wakefd breaks XvcConnection::readTo()'s select()).
    auto xvc = std::make_shared<rpx::Xvc>(0);
    xvc->start();
    uint16_t port = static_cast<uint16_t>(xvc->getPort());
    REQUIRE(port != 0);
    std::this_thread::sleep_for(std::chrono::milliseconds(20));

    // Client: connect but send no bytes → forces XvcConnection::readTo() to
    // block inside select().
    int c = ::socket(AF_INET, SOCK_STREAM, 0);
    REQUIRE(c >= 0);
    // RAII guard so c is closed on any exit path (including exceptions from stop()).
    auto closeC = [&c]() {
        if (c >= 0) {
            ::close(c);
            c = -1;
        }
    };
    sockaddr_in a{};
    a.sin_family      = AF_INET;
    a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    a.sin_port        = htons(port);
    if (::connect(c, reinterpret_cast<sockaddr*>(&a), sizeof(a)) != 0) {
        closeC();
        FAIL("connect() failed");
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(20));

    auto t0      = std::chrono::steady_clock::now();
    xvc->stop();
    auto elapsed = std::chrono::steady_clock::now() - t0;
    closeC();
    auto ms      = std::chrono::duration_cast<std::chrono::milliseconds>(elapsed).count();

    INFO("Xvc::stop() latency with active conn: " << ms << " ms (budget " << kMaxStopLatency.count() << " ms)");
    CHECK(elapsed < kMaxStopLatency);
}
