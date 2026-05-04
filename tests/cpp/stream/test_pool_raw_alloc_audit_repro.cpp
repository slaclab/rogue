/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression tests for Pool::allocBuffer uses raw malloc/free for buffer
 * allocation.  The raw malloc/free pattern is inconsistent with the codebase
 * norm of RAII (std::vector / unique_ptr) and makes future Pool subclasses
 * error-prone.
 *
 * Source-text invariant test: reads Pool.cpp and asserts the allocBuffer
 * function does NOT use raw malloc.  On HEAD it does.
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

TEST_CASE("Pool::allocBuffer uses raw malloc") {
    const std::string src = readFile(
        ROGUE_SRC_DIR "/src/rogue/interfaces/stream/Pool.cpp");
    REQUIRE_MESSAGE(!src.empty(), "Could not read stream/Pool.cpp");

    // Locate the allocBuffer function definition (not the call site)
    const std::size_t pos = src.find("Pool::allocBuffer(");
    REQUIRE_MESSAGE(pos != std::string::npos,
                    "Pool::allocBuffer definition not found in stream/Pool.cpp");

    const std::string region = src.substr(pos, 600);

    // FIXED state: raw malloc replaced with new uint8_t[] or std::vector
    const bool hasMalloc = (region.find("malloc(") != std::string::npos);
    CHECK_MESSAGE(!hasMalloc,
                  "Pool::allocBuffer uses raw malloc for buffer "
                  "allocation; inconsistent with RAII codebase norm; future "
                  "Pool subclasses can easily miss the paired free()");
}
