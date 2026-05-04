/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression tests for Block::setBytes byte-reversed path allocates buff
 * with malloc and has three distinct free() exit paths; a future code-path
 * addition can easily miss the free, leaking the buffer.
 *
 * Source-text invariant test: reads Block.cpp and asserts the byte-reverse
 * path uses RAII (unique_ptr / vector) rather than raw malloc+free.
 * On HEAD the fix is absent -> CHECK_MESSAGE fires.
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

TEST_CASE("setBytes byte-reverse path 3 distinct free() exit paths") {
    const std::string src = readFile(
        ROGUE_SRC_DIR "/src/rogue/interfaces/memory/Block.cpp");
    REQUIRE_MESSAGE(!src.empty(), "Could not read Block.cpp");

    // The byte-reverse malloc site is near: "buff =... malloc(var->valueBytes_)"
    // (around line 666).  Locate it via the unique sentinel.
    const std::string sentinel = "var->valueBytes_))";
    const std::size_t pos = src.find(sentinel);
    REQUIRE_MESSAGE(pos != std::string::npos,
                    "Could not locate byte-reverse malloc sentinel in Block.cpp");

    // Extract the surrounding 2000 bytes covering the setBytes body
    const std::size_t startPos = (pos > 200) ? (pos - 200) : 0;
    const std::string window = src.substr(startPos, 2000);

    // FIXED state: the byte-reverse buff is managed by RAII (unique_ptr or
    // std::vector), so raw "free(buff)" does not appear in this region.
    const bool hasRawFree = (window.find("free(buff)") != std::string::npos);
    CHECK_MESSAGE(!hasRawFree,
                  "setBytes byte-reverse has 3 distinct free() exit "
                  "paths; future addition can skip the free and leak the buffer; "
                  "should use std::unique_ptr<uint8_t[]> for RAII cleanup");
}
