/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression tests for memory::TcpServer::runThread send loop calls
 * zmq_sendmsg() six times but ignores the return value on all calls; a
 * partial multi-part message leaves the PUSH socket in an undefined state
 * without any error propagation.
 *
 * Source-text invariant test: reads TcpServer.cpp and verifies each
 * zmq_sendmsg call has a return-code check.  On HEAD all 6 calls ignore
 * the return value.
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

TEST_CASE("TcpServer runThread send loop ignores zmq_sendmsg returns") {
    const std::string src = readFile(
        ROGUE_SRC_DIR "/src/rogue/interfaces/memory/TcpServer.cpp");
    REQUIRE_MESSAGE(!src.empty(), "Could not read memory/TcpServer.cpp");

    // The send loop in runThread: "for (x = 0; x < 6; x++) zmq_sendmsg(...)"
    // Locate it via the unique loop sentinel.
    const std::string sentinel = "zmq_sendmsg";
    const std::size_t pos = src.find(sentinel);
    REQUIRE_MESSAGE(pos != std::string::npos,
                    "zmq_sendmsg not found in memory/TcpServer.cpp");

    // Extract the region around the send loop (200 bytes before, 300 after)
    const std::size_t startPos = (pos > 200) ? (pos - 200) : 0;
    const std::string region   = src.substr(startPos, 500);

    // FIXED state: zmq_sendmsg return value is checked (assigned to a
    // variable or used in an if/while condition).
    // On HEAD: "for (x...) zmq_sendmsg(...,...)" -- return value discarded.
    const bool returnsChecked = (
        region.find("= zmq_sendmsg(") != std::string::npos ||
        region.find("if (zmq_sendmsg(") != std::string::npos ||
        region.find("if(zmq_sendmsg(") != std::string::npos ||
        region.find("rc = zmq_sendmsg") != std::string::npos ||
        region.find("ret = zmq_sendmsg") != std::string::npos);

    CHECK_MESSAGE(returnsChecked,
                  "TcpServer runThread send loop ignores "
                  "zmq_sendmsg return code; partial multi-part message "
                  "leaves PUSH socket in undefined state without error "
                  "propagation to caller");
}
