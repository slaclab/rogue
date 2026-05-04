/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression tests for stream::TcpCore::close() is marked "deprecated"
 * in a comment at TcpCore.cpp line ~186 but has no [[deprecated]] attribute
 * in the header; callers cannot detect the deprecation at compile time.
 *
 * Source-text invariant test: reads the TcpCore header and asserts that
 * [[deprecated]] appears near the close() declaration.  On HEAD it is absent.
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

TEST_CASE("stream::TcpCore::close() missing [[deprecated]]") {
    const std::string hdr = readFile(
        ROGUE_SRC_DIR "/include/rogue/interfaces/stream/TcpCore.h");
    REQUIRE_MESSAGE(!hdr.empty(), "Could not read stream/TcpCore.h");

    // Locate the close() declaration in the header
    const std::size_t closePos = hdr.find("close()");
    REQUIRE_MESSAGE(closePos != std::string::npos,
                    "close() declaration not found in stream/TcpCore.h");

    // Check the 200 bytes around close() for [[deprecated]]
    const std::size_t startPos = (closePos > 100) ? (closePos - 100) : 0;
    const std::string region   = hdr.substr(startPos, 300);

    const bool hasDeprecated = (
        region.find("[[deprecated]]") != std::string::npos ||
        region.find("[[deprecated(") != std::string::npos  ||
        region.find("__attribute__((deprecated") != std::string::npos);

    CHECK_MESSAGE(hasDeprecated,
                  "stream::TcpCore::close() is marked deprecated "
                  "in a comment only; [[deprecated]] attribute is missing from "
                  "the header declaration; callers get no compile-time warning");
}
