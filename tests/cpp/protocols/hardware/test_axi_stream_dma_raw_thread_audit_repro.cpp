/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression tests
 * hardware::axi::AxiStreamDma constructor allocates its worker thread via
 * ``new std::thread`` stored in a raw ``thread_`` pointer with a try/catch
 * guard.  Same raw-ptr tech debt as  and.
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

TEST_CASE("hardware::AxiStreamDma uses RAII thread allocation") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/hardware/axi/AxiStreamDma.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "AxiStreamDma.cpp not found at " << path);

    const bool hasRaw = src.find("new std::thread") != std::string::npos;
    CHECK_MESSAGE(!hasRaw,
        " regression: raw 'new std::thread' is back in hardware/axi/AxiStreamDma.cpp; "
        "fix replaced it with std::make_unique<std::thread>");

    const bool hasRaiiThread =
        src.find("make_unique<std::thread>") != std::string::npos ||
        src.find("unique_ptr<std::thread>") != std::string::npos;
    CHECK_MESSAGE(hasRaiiThread,
        "AxiStreamDma.cpp must allocate worker thread via "
        "std::make_unique<std::thread> or std::unique_ptr<std::thread>");
}
