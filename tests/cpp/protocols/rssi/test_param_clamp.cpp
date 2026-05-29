/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression: rpr::Controller::clampPeerParams() clamps peer-advertised RSSI
 * connection parameters to the locally legal range. The SYN/SYN-ACK handshake
 * adopts the peer's advertised parameters verbatim; an out-of-range peer value
 * (zero outstanding segments, zero timeouts, a sub-header-size segment, or a
 * window larger than the locally offered maximum) would otherwise drive the
 * controller into illegal state (for example curMaxBuffers == 0 makes the
 * outbound wait loop spin forever). Conformant peers, including SLAC firmware,
 * must be left untouched.
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

#include <cstdint>

#include "doctest/doctest.h"
#include "rogue/protocols/rssi/Controller.h"
#include "rogue/protocols/rssi/Header.h"

namespace rpr = rogue::protocols::rssi;

// Local bounds used by the tests (rogue defaults: 32 buffers, 1400 byte segment)
static const uint8_t kLocMaxBuffers  = 32;
static const uint16_t kLocMaxSegment = 1400;

TEST_CASE("clampPeerParams leaves a conformant peer untouched") {
    uint8_t maxBuffers  = 8;
    uint16_t maxSegment = 512;
    uint16_t cumAckTout = 5;
    uint16_t retranTout = 20;
    uint16_t nullTout   = 1000;

    bool clamped = rpr::Controller::clampPeerParams(maxBuffers,
                                                    maxSegment,
                                                    cumAckTout,
                                                    retranTout,
                                                    nullTout,
                                                    kLocMaxBuffers,
                                                    kLocMaxSegment);

    CHECK_FALSE(clamped);
    CHECK_EQ(maxBuffers, static_cast<uint8_t>(8));
    CHECK_EQ(maxSegment, static_cast<uint16_t>(512));
    CHECK_EQ(cumAckTout, static_cast<uint16_t>(5));
    CHECK_EQ(retranTout, static_cast<uint16_t>(20));
    CHECK_EQ(nullTout, static_cast<uint16_t>(1000));
}

TEST_CASE("clampPeerParams raises a zero outstanding-segment count to 1") {
    uint8_t maxBuffers  = 0;
    uint16_t maxSegment = 512;
    uint16_t cumAckTout = 5;
    uint16_t retranTout = 20;
    uint16_t nullTout   = 1000;

    bool clamped = rpr::Controller::clampPeerParams(maxBuffers,
                                                    maxSegment,
                                                    cumAckTout,
                                                    retranTout,
                                                    nullTout,
                                                    kLocMaxBuffers,
                                                    kLocMaxSegment);

    CHECK(clamped);
    CHECK_EQ(maxBuffers, static_cast<uint8_t>(1));
}

TEST_CASE("clampPeerParams caps an oversized window at the local maximum") {
    uint8_t maxBuffers  = 200;
    uint16_t maxSegment = 512;
    uint16_t cumAckTout = 5;
    uint16_t retranTout = 20;
    uint16_t nullTout   = 1000;

    bool clamped = rpr::Controller::clampPeerParams(maxBuffers,
                                                    maxSegment,
                                                    cumAckTout,
                                                    retranTout,
                                                    nullTout,
                                                    kLocMaxBuffers,
                                                    kLocMaxSegment);

    CHECK(clamped);
    CHECK_EQ(maxBuffers, kLocMaxBuffers);
}

TEST_CASE("clampPeerParams raises a sub-header segment size to the header size") {
    uint8_t maxBuffers  = 8;
    uint16_t maxSegment = 4;  // smaller than the 8-byte header
    uint16_t cumAckTout = 5;
    uint16_t retranTout = 20;
    uint16_t nullTout   = 1000;

    bool clamped = rpr::Controller::clampPeerParams(maxBuffers,
                                                    maxSegment,
                                                    cumAckTout,
                                                    retranTout,
                                                    nullTout,
                                                    kLocMaxBuffers,
                                                    kLocMaxSegment);

    CHECK(clamped);
    CHECK_EQ(maxSegment, static_cast<uint16_t>(rpr::Header::HeaderSize));
}

TEST_CASE("clampPeerParams caps an oversized segment at the local maximum") {
    uint8_t maxBuffers  = 8;
    uint16_t maxSegment = 9000;  // larger than locally offered
    uint16_t cumAckTout = 5;
    uint16_t retranTout = 20;
    uint16_t nullTout   = 1000;

    bool clamped = rpr::Controller::clampPeerParams(maxBuffers,
                                                    maxSegment,
                                                    cumAckTout,
                                                    retranTout,
                                                    nullTout,
                                                    kLocMaxBuffers,
                                                    kLocMaxSegment);

    CHECK(clamped);
    CHECK_EQ(maxSegment, kLocMaxSegment);
}

TEST_CASE("clampPeerParams raises zero timeouts to 1") {
    uint8_t maxBuffers  = 8;
    uint16_t maxSegment = 512;
    uint16_t cumAckTout = 0;
    uint16_t retranTout = 0;
    uint16_t nullTout   = 0;

    bool clamped = rpr::Controller::clampPeerParams(maxBuffers,
                                                    maxSegment,
                                                    cumAckTout,
                                                    retranTout,
                                                    nullTout,
                                                    kLocMaxBuffers,
                                                    kLocMaxSegment);

    CHECK(clamped);
    CHECK_EQ(cumAckTout, static_cast<uint16_t>(1));
    CHECK_EQ(retranTout, static_cast<uint16_t>(1));
    CHECK_EQ(nullTout, static_cast<uint16_t>(1));
}

TEST_CASE("clampPeerParams clamps multiple out-of-range fields at once") {
    uint8_t maxBuffers  = 0;
    uint16_t maxSegment = 0;
    uint16_t cumAckTout = 0;
    uint16_t retranTout = 0;
    uint16_t nullTout   = 0;

    bool clamped = rpr::Controller::clampPeerParams(maxBuffers,
                                                    maxSegment,
                                                    cumAckTout,
                                                    retranTout,
                                                    nullTout,
                                                    kLocMaxBuffers,
                                                    kLocMaxSegment);

    CHECK(clamped);
    CHECK_EQ(maxBuffers, static_cast<uint8_t>(1));
    CHECK_EQ(maxSegment, static_cast<uint16_t>(rpr::Header::HeaderSize));
    CHECK_EQ(cumAckTout, static_cast<uint16_t>(1));
    CHECK_EQ(retranTout, static_cast<uint16_t>(1));
    CHECK_EQ(nullTout, static_cast<uint16_t>(1));
}
