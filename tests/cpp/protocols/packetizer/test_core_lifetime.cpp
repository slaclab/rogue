/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression: rpp::Core / rpp::CoreV2 destruction must release the Transport
 * and Controller. Controller and Transport previously held shared_ptrs to each
 * other, leaking the "PackTrans" thread, and Controller::app_ pointed into the
 * freed Core, so a packet arriving through an upstream master that still held
 * the Transport dereferenced freed memory in transportRx().
 * ----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to
 * the license terms in the LICENSE.txt file found in the top-level directory
 * of this distribution and at:
 *    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
 * No part of the rogue software platform, including this file, may be
 * copied, modified, propagated, or distributed except according to the terms
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
 */

#include <chrono>
#include <cstdint>
#include <memory>
#include <thread>
#include <vector>

#include "doctest/doctest.h"
#include "support/test_helpers.h"

#include "rogue/GeneralError.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/protocols/packetizer/Application.h"
#include "rogue/protocols/packetizer/Core.h"
#include "rogue/protocols/packetizer/CoreV2.h"
#include "rogue/protocols/packetizer/Transport.h"

namespace ris = rogue::interfaces::stream;
namespace rpp = rogue::protocols::packetizer;

namespace {

// Single-segment V1 frame to dest 0: 64-bit header, 8 payload bytes, EOF tail.
std::vector<uint8_t> makeV1Frame() {
    std::vector<uint8_t> f(17, 0);
    for (uint8_t i = 0; i < 8; i++) f[8 + i] = static_cast<uint8_t>(0xA0 + i);
    f[16] = 0x80;  // EOF
    return f;
}

// Single-segment V2 frame to dest 0 (no CRC): header, one payload word, tail.
std::vector<uint8_t> makeV2Frame() {
    std::vector<uint8_t> f(24, 0);
    f[0] = 0x02;  // Version 2
    f[7] = 0x80;  // SOF
    for (uint8_t i = 0; i < 8; i++) f[8 + i] = static_cast<uint8_t>(0xA0 + i);
    f[17] = 0x01;  // EOF
    f[18] = 8;     // last
    return f;
}

struct V1 {
    static std::shared_ptr<rpp::Core> create() {
        return rpp::Core::create(false);
    }
    static std::vector<uint8_t> frame() {
        return makeV1Frame();
    }
};

struct V2 {
    static std::shared_ptr<rpp::CoreV2> create() {
        return rpp::CoreV2::create(false, false, false);
    }
    static std::vector<uint8_t> frame() {
        return makeV2Frame();
    }
};

}  // namespace

TEST_CASE_TEMPLATE("packetizer core destruction releases the transport", T, V1, V2) {
    auto core                           = T::create();
    std::weak_ptr<rpp::Transport> tran  = core->transport();
    std::weak_ptr<rpp::Application> app = core->application(0);

    core.reset();

    CHECK(tran.expired());
    CHECK(app.expired());
}

TEST_CASE_TEMPLATE("packetizer transport held upstream is safe after core destruction", T, V1, V2) {
    auto core   = T::create();
    auto slave  = ris::Slave::create();
    auto master = ris::Master::create();
    auto pool   = rogue_test::makePool();

    // Keep the application alive past the Core to cover its expired-controller paths.
    rpp::ApplicationPtr app = core->application(0);
    app->addSlave(slave);
    master->addSlave(core->transport());
    std::weak_ptr<rpp::Transport> tran = core->transport();

    master->sendFrame(rogue_test::makeFrame(pool, T::frame()));
    REQUIRE(rogue_test::waitUntil([&]() { return slave->getFrameCount() == 1; }));

    core.reset();
    CHECK_FALSE(tran.expired());

    // Upstream master still holds the transport; this packet must be dropped.
    CHECK_NOTHROW(master->sendFrame(rogue_test::makeFrame(pool, T::frame())));
    std::this_thread::sleep_for(std::chrono::milliseconds(20));
    CHECK_EQ(slave->getFrameCount(), 1u);

    // Application endpoint outliving the Core drops writes and rejects allocations.
    auto appMaster = ris::Master::create();
    appMaster->addSlave(app);
    CHECK_NOTHROW(appMaster->sendFrame(rogue_test::makeFrame(pool, T::frame())));
    CHECK_THROWS_AS(appMaster->reqFrame(64, true), rogue::GeneralError);

    master.reset();
    CHECK(tran.expired());
}
