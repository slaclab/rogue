/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression: rpp::ControllerV2::transportRx must validate the tail "last"
 * field (valid byte count in the final 64-bit word, legal range 1..8). An
 * out-of-range value previously flowed straight into Buffer::adjustPayload,
 * either leaving tail bytes in the payload, growing the payload into bytes
 * that were never received, or throwing GeneralError out of
 * Transport::acceptFrame on the upstream receiver's thread.
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

#include <chrono>
#include <cstdint>
#include <thread>
#include <vector>

#include "doctest/doctest.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/protocols/packetizer/Application.h"
#include "rogue/protocols/packetizer/CoreV2.h"
#include "rogue/protocols/packetizer/Transport.h"
#include "support/test_helpers.h"

namespace ris = rogue::interfaces::stream;
namespace rpp = rogue::protocols::packetizer;

namespace {

// Minimal single-segment V2 frame (no CRC): 64-bit header, one 64-bit
// payload word, 64-bit tail. SOF and EOF are both set so the frame is
// complete on its own and would be forwarded to the application endpoint.
std::vector<uint8_t> makeV2Frame(uint8_t last) {
    std::vector<uint8_t> f(24, 0);

    // Header word 0: version 2, fuser, dest 0, id 0
    f[0] = 0x02;
    f[1] = 0x00;
    f[2] = 0x00;
    f[3] = 0x00;

    // Header word 1: count 0, SOF
    f[7] = 0x80;

    // Payload word
    for (uint8_t i = 0; i < 8; i++) f[8 + i] = static_cast<uint8_t>(0xA0 + i);

    // Tail word 0: luser, EOF, last
    f[16] = 0x00;
    f[17] = 0x01;
    f[18] = last;

    return f;
}

}  // namespace

TEST_CASE("ControllerV2 drops frames with an out-of-range tail last value") {
    auto core   = rpp::CoreV2::create(false, false, false);
    auto app    = core->application(0);
    auto slave  = ris::Slave::create();
    auto master = ris::Master::create();
    auto pool   = rogue_test::makePool();

    app->addSlave(slave);
    master->addSlave(core->transport());

    uint8_t last = 0;
    SUBCASE("last = 0") { last = 0; }
    SUBCASE("last = 9") { last = 9; }
    SUBCASE("last = 0xFF") { last = 0xFF; }

    CHECK_NOTHROW(master->sendFrame(rogue_test::makeFrame(pool, makeV2Frame(last))));

    CHECK_EQ(core->getDropCount(), 1u);

    // Give the application thread a chance to forward anything it was handed.
    std::this_thread::sleep_for(std::chrono::milliseconds(20));
    CHECK_EQ(slave->getFrameCount(), 0u);
}

TEST_CASE("ControllerV2 forwards frames with a valid tail last value") {
    auto core   = rpp::CoreV2::create(false, false, false);
    auto app    = core->application(0);
    auto slave  = ris::Slave::create();
    auto master = ris::Master::create();
    auto pool   = rogue_test::makePool();

    app->addSlave(slave);
    master->addSlave(core->transport());

    uint8_t last = 0;
    SUBCASE("last = 1") { last = 1; }
    SUBCASE("last = 8") { last = 8; }

    CHECK_NOTHROW(master->sendFrame(rogue_test::makeFrame(pool, makeV2Frame(last))));

    CHECK(rogue_test::waitUntil([&]() { return slave->getFrameCount() == 1; }));
    CHECK_EQ(core->getDropCount(), 0u);
    CHECK_EQ(slave->getByteCount(), static_cast<uint64_t>(last));
}
