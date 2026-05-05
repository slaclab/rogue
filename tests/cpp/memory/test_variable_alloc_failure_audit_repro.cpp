/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression tests for Variable ctor allocates lowTranByte_,
 * highTranByte_, and optionally fastByte_ with malloc; if the second or
 * third malloc fails, earlier allocations are silently leaked because the
 * Variable dtor only frees non-NULL members.
 *
 * Source-text invariant test: reads Variable.cpp and asserts the ctor uses
 * RAII (unique_ptr / vector) rather than raw malloc.  On HEAD the fix is
 * absent -> CHECK_MESSAGE fires.
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

TEST_CASE("Variable ctor 3x malloc partial-leak on second/third NULL") {
    const std::string src = readFile(
        ROGUE_SRC_DIR "/src/rogue/interfaces/memory/Variable.cpp");
    REQUIRE_MESSAGE(!src.empty(), "Could not read Variable.cpp");

    // Locate the ctor region via the sentinel "lowTranByte_" which is the
    // first of the three malloc'd members (around line 180).
    const std::string sentinel = "lowTranByte_";
    const std::size_t pos = src.find(sentinel);
    REQUIRE_MESSAGE(pos != std::string::npos,
                    "Could not locate lowTranByte_ sentinel in Variable.cpp");

    // Extract the next 1200 bytes covering all three malloc calls
    const std::string window = src.substr(pos, 1200);

    // FIXED state: malloc calls replaced with std::unique_ptr or std::vector,
    // so raw "malloc(" does not appear in this region of the ctor.
    const bool hasMalloc = (window.find("malloc(") != std::string::npos);
    CHECK_MESSAGE(!hasMalloc,
                  "Variable ctor 3x malloc; partial-leak on second/"
                  "third NULL return; should use std::unique_ptr or "
                  "std::vector to guarantee exception-safe cleanup");
}
