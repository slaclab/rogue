/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression tests for Emulate::doTransaction calls malloc(0x1000)
 * without checking for NULL; a NULL return would silently insert a NULL
 * pointer into memMap_, causing a subsequent memcpy crash.
 *
 * Source-text invariant test: reads Emulate.cpp and asserts the malloc
 * result is checked for NULL (or replaced with RAII) before the pointer
 * is inserted into memMap_.  On HEAD the check is absent.
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

TEST_CASE("Emulate::doTransaction malloc(0x1000) without NULL check") {
    const std::string src = readFile(
        ROGUE_SRC_DIR "/src/rogue/interfaces/memory/Emulate.cpp");
    REQUIRE_MESSAGE(!src.empty(), "Could not read Emulate.cpp");

    // Locate the malloc call near the memMap_ insert (around line 90).
    // The sentinel "malloc(0x1000)" uniquely identifies the allocation site.
    const std::string sentinel = "malloc(0x1000)";
    const std::size_t pos = src.find(sentinel);
    REQUIRE_MESSAGE(pos != std::string::npos,
                    "malloc(0x1000) not found in Emulate.cpp; "
                    "maybe already replaced with RAII?");

    // Extract the 10 lines after the malloc call to check for NULL guard
    const std::string window = src.substr(pos, 400);

    // FIXED state: after malloc(0x1000), there is a NULL check before insert.
    // Look for patterns like "== NULL", "!= NULL", "nullptr", or the allocation
    // uses RAII (std::make_unique / new uint8_t[]).
    const bool hasNullCheck = (
        window.find("== NULL") != std::string::npos ||
        window.find("!= NULL") != std::string::npos ||
        window.find("== nullptr") != std::string::npos ||
        window.find("!= nullptr") != std::string::npos ||
        window.find("make_unique") != std::string::npos);

    CHECK_MESSAGE(hasNullCheck,
                  "Emulate::doTransaction malloc(0x1000) result "
                  "inserted into memMap_ without NULL check; a NULL page "
                  "pointer would crash on the subsequent memcpy call");
}
