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

// Locate every occurrence of `needle` in `hay`, and for each one decide
// whether the surrounding source text places the call in a "checked" context
// (assignment to a variable, or used as part of an if/while predicate).  A
// single bare statement counts as unchecked.
static bool everyCallIsChecked(const std::string& hay, const std::string& needle) {
    if (hay.find(needle) == std::string::npos) return false;

    std::size_t pos = 0;
    while ((pos = hay.find(needle, pos)) != std::string::npos) {
        // Walk back through whitespace to the previous non-space character
        std::size_t i = pos;
        while (i > 0 && (hay[i - 1] == ' ' || hay[i - 1] == '\t' || hay[i - 1] == '\n')) {
            --i;
        }
        // Acceptable preceding contexts:
        //   "= zmq_sendmsg("   (return code captured)
        //   "(zmq_sendmsg("    (used inside an expression / predicate)
        //   "!zmq_sendmsg("    (boolean negation as predicate)
        const char prev = (i > 0) ? hay[i - 1] : '\0';
        const bool checked = (prev == '=' || prev == '(' || prev == '!' ||
                              prev == '<' || prev == '>' || prev == ',' ||
                              prev == '?' || prev == ':' || prev == '|' ||
                              prev == '&');
        if (!checked) return false;
        pos += needle.size();
    }
    return true;
}

TEST_CASE("TcpServer runThread send loop ignores zmq_sendmsg returns") {
    const std::string src = readFile(
        ROGUE_SRC_DIR "/src/rogue/interfaces/memory/TcpServer.cpp");
    REQUIRE_MESSAGE(!src.empty(), "Could not read memory/TcpServer.cpp");

    // Confirm the call exists at all
    REQUIRE_MESSAGE(src.find("zmq_sendmsg") != std::string::npos,
                    "zmq_sendmsg not found in memory/TcpServer.cpp");

    // Every zmq_sendmsg call in the entire translation unit must be in a
    // checked context.  This is stronger than a single nearby-window check:
    // a partial fix that wraps one call in an if() while leaving five other
    // bare calls in an unrolled loop will fail this assertion, even though
    // the old window-based scan would have accepted it.
    const bool allChecked = everyCallIsChecked(src, "zmq_sendmsg(");

    CHECK_MESSAGE(allChecked,
                  "TcpServer runThread send loop ignores "
                  "zmq_sendmsg return code; partial multi-part message "
                  "leaves PUSH socket in undefined state without error "
                  "propagation to caller (every zmq_sendmsg call in the "
                  "file must be assigned, predicated, or otherwise "
                  "consumed -- bare-statement calls are not accepted)");
}
