/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Audit repro for IFCE-001: Block ctor 5x malloc with no exception-safe
 * cleanup.  If any of the five malloc calls returns NULL and throws, the
 * earlier allocated buffers are leaked because the Block dtor only runs
 * free() on members whose pointers were successfully initialised.
 *
 * Source-text invariant test: reads Block.cpp and asserts a structural
 * property that the fixed code must satisfy.  On HEAD the fix is absent.
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

TEST_CASE("IFCE-001: Block ctor 5x malloc partial-allocation leak") {
    const std::string src = readFile(
        ROGUE_SRC_DIR "/src/rogue/interfaces/memory/Block.cpp");
    REQUIRE_MESSAGE(!src.empty(), "Could not read Block.cpp");

    // The structural invariant: the five consecutive malloc calls in the ctor
    // must be wrapped in a try/catch or use RAII (std::vector / unique_ptr).
    // Locate the ctor region via the sentinel "verifyBase_ = 0;" which appears
    // just before the five malloc calls.
    const std::string sentinel = "verifyBase_ = 0;";
    const std::size_t pos = src.find(sentinel);
    REQUIRE_MESSAGE(pos != std::string::npos,
                    "Could not locate Block ctor sentinel in Block.cpp");

    // Extract the next 800 bytes covering all 5 malloc calls
    const std::string window = src.substr(pos, 800);

    // FIXED state: malloc calls replaced with std::vector or unique_ptr
    // (so "malloc(" does not appear in the ctor), OR the malloc block is
    // wrapped in try/catch.
    const bool hasMalloc    = (window.find("malloc(") != std::string::npos);
    const bool hasTryCatch  = (window.find("try {") != std::string::npos ||
                                window.find("try{") != std::string::npos);
    const bool isFixed      = !hasMalloc || hasTryCatch;

    CHECK_MESSAGE(isFixed,
                  "IFCE-001: Block ctor 5x malloc; partial-allocation throw "
                  "leaks earlier buffers (no RAII / no try-catch wrapper "
                  "around the 5 successive malloc calls)");
}
