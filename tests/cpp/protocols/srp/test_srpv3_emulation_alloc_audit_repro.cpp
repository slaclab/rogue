/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Audit repro for PROT-007:
 * SrpV3Emulation::allocatePage() allocates each 4 KiB emulated memory page
 * via raw ``malloc(0x1000)`` and stores the raw pointer in the ``memMap_``
 * std::map.  If the map::insert call throws std::bad_alloc after malloc
 * succeeds, the allocated page is leaked because no RAII owner holds it.
 * A correct implementation uses std::unique_ptr<uint8_t[]> or
 * std::make_unique<uint8_t[]>(0x1000).
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

#include <fstream>
#include <sstream>
#include <string>

#include "doctest/doctest.h"

#ifndef ROGUE_SRC_DIR
    #error "ROGUE_SRC_DIR must be defined via target_compile_definitions"
#endif

static std::string readFile(const std::string& path) {
    std::ifstream f(path);
    if (!f.is_open()) return "";
    std::ostringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

/// Extract up to maxLines lines starting at the line that contains marker.
static std::string extractContext(const std::string& src,
                                  const std::string& marker,
                                  int maxLines) {
    std::istringstream ss(src);
    std::string line;
    std::ostringstream out;
    bool inFunc   = false;
    int count     = 0;
    while (std::getline(ss, line)) {
        if (!inFunc && line.find(marker) != std::string::npos) inFunc = true;
        if (inFunc) {
            out << line << "\n";
            if (++count >= maxLines) break;
        }
    }
    return out.str();
}

TEST_CASE("PROT-007: SrpV3Emulation::allocatePage uses RAII page allocation") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/protocols/srp/SrpV3Emulation.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "SrpV3Emulation.cpp not found at " << path);

    // Scope the RAII check to the allocatePage function body.
    // std::vector<uint8_t> used elsewhere in processFrame does NOT fix the
    // page-allocation leak — the fix must be in allocatePage itself.
    const std::string funcBody = extractContext(src, "allocatePage(uint64_t addr4k)", 30);
    REQUIRE_MESSAGE(!funcBody.empty(),
        "PROT-007: allocatePage function not found in SrpV3Emulation.cpp");

    const bool hasRawMalloc = funcBody.find("malloc(0x1000)") != std::string::npos;
    CHECK_MESSAGE(!hasRawMalloc,
        "PROT-007 regression: raw 'malloc(0x1000)' is back in allocatePage; "
        "fix(PROT-007) replaced it with std::make_unique<uint8_t[]>(0x1000)");

    const bool hasRAII =
        funcBody.find("unique_ptr<uint8_t") != std::string::npos ||
        funcBody.find("make_unique<uint8_t") != std::string::npos;
    CHECK_MESSAGE(hasRAII,
        "PROT-007: allocatePage must use std::make_unique<uint8_t[]>(0x1000) "
        "or std::unique_ptr<uint8_t[]> for RAII ownership of the 4K page");
}
