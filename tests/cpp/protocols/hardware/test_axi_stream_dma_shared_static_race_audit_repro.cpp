/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression tests
 * AxiStreamDma.cpp declares ``sharedBuffers_`` as a file-scope static
 * std::map at line ~45.  openShared() (called from the constructor) and
 * closeShared() (called from the destructor) access this map without any
 * mutex protection.  Concurrent construction of two AxiStreamDma objects
 * on separate threads races on the static map, potentially corrupting it.
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

TEST_CASE("AxiStreamDma sharedBuffers_ static map accessed without mutex") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/hardware/axi/AxiStreamDma.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "AxiStreamDma.cpp not found at " << path);

    // Confirm the static sharedBuffers_ map exists
    REQUIRE_MESSAGE(src.find("sharedBuffers_") != std::string::npos,
        "sharedBuffers_ not found in AxiStreamDma.cpp; file may have changed");

    // A mutex must guard all accesses to sharedBuffers_.  Look for a mutex
    // declaration adjacent to sharedBuffers_ or a lock_guard in openShared/closeShared.
    // Check for a static mutex in the same translation unit.
    const bool hasMutex =
        src.find("sharedBuffersMtx") != std::string::npos ||
        src.find("sharedMtx") != std::string::npos ||
        src.find("sharedBuffers_Mtx") != std::string::npos ||
        src.find("static std::mutex") != std::string::npos;

    CHECK_MESSAGE(hasMutex,
        " regression: AxiStreamDma must declare a static std::mutex "
        "(e.g. sharedBuffersMtx) and lock it around all accesses to "
        "sharedBuffers_ in openShared/closeShared; fix added "
        "'static std::mutex sharedBuffersMtx;' to prevent concurrent "
        "AxiStreamDma construction from racing on the file-scope static map");
}
