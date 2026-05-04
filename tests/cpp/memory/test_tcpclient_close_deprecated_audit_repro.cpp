/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression tests for memory::TcpClient::close() is marked "deprecated"
 * in a comment at TcpClient.cpp line ~163 but has no [[deprecated]] attribute
 * in the header; callers cannot detect the deprecation at compile time.
 *
 * Source-text invariant test: reads the TcpClient header and asserts that
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

TEST_CASE("memory::TcpClient::close() missing [[deprecated]]") {
    const std::string hdr = readFile(
        ROGUE_SRC_DIR "/include/rogue/interfaces/memory/TcpClient.h");
    REQUIRE_MESSAGE(!hdr.empty(), "Could not read memory/TcpClient.h");

    // Locate the close() declaration in the header.
    const std::size_t closePos = hdr.find("close()");
    REQUIRE_MESSAGE(closePos != std::string::npos,
                    "close() declaration not found in memory/TcpClient.h");

    // Check the 200 bytes around close() for [[deprecated]]
    const std::size_t startPos = (closePos > 100) ? (closePos - 100) : 0;
    const std::string region   = hdr.substr(startPos, 300);

    const bool hasDeprecated = (
        region.find("[[deprecated]]") != std::string::npos ||
        region.find("[[deprecated(") != std::string::npos  ||
        region.find("__attribute__((deprecated") != std::string::npos);

    CHECK_MESSAGE(hasDeprecated,
                  "memory::TcpClient::close() is marked deprecated "
                  "in a comment only; [[deprecated]] attribute is missing from "
                  "the header declaration; callers get no compile-time warning");
}
