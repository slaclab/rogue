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

    // Two acceptable fix shapes for the original bug (silent NULL insert
    // into memMap_ followed by a memcpy crash):
    //   (a) malloc(0x1000) with an explicit NULL/nullptr guard before insert
    //   (b) RAII allocation (std::make_unique / new uint8_t[] held by a
    //       unique_ptr) which throws std::bad_alloc instead of returning NULL
    //
    // The window is scoped near whichever allocation form is present so the
    // check actually exercises the page-allocation site, not unrelated
    // allocations elsewhere in the file.
    const std::size_t mallocPos    = src.find("malloc(0x1000)");
    const std::size_t makeUniquePos = src.find("std::make_unique<uint8_t[]>(0x1000)");
    const std::size_t newArrayPos  = src.find("new uint8_t[0x1000]");

    const bool hasMalloc     = (mallocPos    != std::string::npos);
    const bool hasMakeUnique = (makeUniquePos != std::string::npos);
    const bool hasNewArray   = (newArrayPos  != std::string::npos);
    const bool hasAnyAlloc   = hasMalloc || hasMakeUnique || hasNewArray;

    REQUIRE_MESSAGE(hasAnyAlloc,
        "Emulate.cpp no longer contains a recognisable 4k page allocation "
        "(malloc(0x1000), std::make_unique<uint8_t[]>(0x1000), or "
        "new uint8_t[0x1000]); update this regression test to track the new form");

    bool guardOk = false;
    if (hasMalloc) {
        // For raw malloc the NULL check must appear before the memMap_.insert
        // that follows the allocation.  Bound the search to a small window so a
        // far-away nullptr token in an unrelated function cannot satisfy it.
        const std::string window = src.substr(mallocPos, 400);
        guardOk = (
            window.find("== NULL")    != std::string::npos ||
            window.find("!= NULL")    != std::string::npos ||
            window.find("== nullptr") != std::string::npos ||
            window.find("!= nullptr") != std::string::npos);
    } else {
        // RAII allocations (make_unique / new uint8_t[] under unique_ptr) throw
        // bad_alloc on failure rather than returning NULL, so the silent-NULL
        // failure mode the original bug describes cannot occur.  We still
        // require unique_ptr ownership at the allocation site so a bare
        // "new uint8_t[...]" leak is not accepted as a fix.
        const std::size_t pos    = hasMakeUnique ? makeUniquePos : newArrayPos;
        const std::string window = src.substr(pos, 400);
        guardOk = hasMakeUnique ||
            (window.find("unique_ptr") != std::string::npos);
    }

    CHECK_MESSAGE(guardOk,
                  "Emulate::doTransaction page allocation result is inserted "
                  "into memMap_ without a NULL/exception-safe guard; a NULL "
                  "page pointer would crash on the subsequent memcpy call");
}
