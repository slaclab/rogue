/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression test for stream::TcpCore::acceptFrame() calling
 * zmq_sendmsg(this->zmqPush_, ...) without guarding zmqPush_ against null.
 *
 * Background:
 *   When a multi-part send fails mid-frame, the recovery path closes and
 *   tries to rebuild zmqPush_.  If the rebuild itself fails, zmqPush_ is
 *   left null.  Without an entry-point guard, the next acceptFrame() call
 *   would invoke zmq_sendmsg(nullptr, ...), which libzmq does not guarantee
 *   is safe across versions.
 *
 * Source-text invariant: the function body of acceptFrame() must contain a
 * nullptr check on zmqPush_ before reaching the zmq_sendmsg call site.  We
 * locate the acceptFrame() definition and assert that a recognizable null
 * guard appears between the function start and its first zmq_sendmsg call.
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

#include <fstream>
#include <sstream>
#include <string>

#include "doctest/doctest.h"

#ifndef ROGUE_SRC_DIR
    #define ROGUE_SRC_DIR "."
#endif

static std::string readFile(const std::string& path) {
    std::ifstream f(path);
    if (!f.is_open()) return std::string();
    std::ostringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

TEST_CASE("stream::TcpCore::acceptFrame guards zmqPush_ against null before zmq_sendmsg") {
    const std::string src = readFile(
        ROGUE_SRC_DIR "/src/rogue/interfaces/stream/TcpCore.cpp");
    REQUIRE_MESSAGE(!src.empty(), "Could not read stream/TcpCore.cpp");

    // Locate the acceptFrame() function definition.
    const std::size_t fnStart = src.find("ris::TcpCore::acceptFrame(");
    REQUIRE_MESSAGE(fnStart != std::string::npos,
                    "TcpCore::acceptFrame() definition not found");

    // Locate the first zmq_sendmsg call after the function start.
    const std::size_t sendPos = src.find("zmq_sendmsg(this->zmqPush_", fnStart);
    REQUIRE_MESSAGE(sendPos != std::string::npos,
                    "zmq_sendmsg(this->zmqPush_, ...) call not found in acceptFrame()");

    const std::string region = src.substr(fnStart, sendPos - fnStart);

    const bool hasNullGuard = (
        region.find("zmqPush_ == nullptr")  != std::string::npos ||
        region.find("zmqPush_ == NULL")     != std::string::npos ||
        region.find("!this->zmqPush_")      != std::string::npos ||
        region.find("!zmqPush_")            != std::string::npos);

    CHECK_MESSAGE(hasNullGuard,
                  "TcpCore::acceptFrame() does not guard zmqPush_ against "
                  "null before invoking zmq_sendmsg; if the post-failure "
                  "rebuild path leaves zmqPush_ null, the next frame can "
                  "trigger zmq_sendmsg(nullptr, ...)");
}
