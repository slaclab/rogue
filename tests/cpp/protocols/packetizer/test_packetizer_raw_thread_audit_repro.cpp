/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression tests
 * Both packetizer::Application::setController() and
 * packetizer::Transport::setController() allocate their worker thread via
 * ``new std::thread`` without a try/catch guard.  If the thread constructor
 * itself throws (OOM), the raw pointer is left dangling and the later stop()
 * call dereferences a null/garbage pointer.
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

/// Return true if the source uses RAII-managed thread allocation
/// (std::make_unique<std::thread> or std::unique_ptr<std::thread>).
static bool threadIsRAII(const std::string& src) {
    return src.find("make_unique<std::thread>") != std::string::npos ||
           src.find("unique_ptr<std::thread>") != std::string::npos;
}

TEST_CASE("packetizer::Application::setController uses RAII thread allocation") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/protocols/packetizer/Application.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "Application.cpp not found at " << path);

    const bool hasRaw = src.find("new std::thread") != std::string::npos;
    CHECK_MESSAGE(!hasRaw,
        " regression: raw 'new std::thread' is back in packetizer/Application.cpp; "
        "fix replaced it with std::make_unique<std::thread>");

    CHECK_MESSAGE(threadIsRAII(src),
        "Application.cpp must allocate worker thread via "
        "std::make_unique<std::thread> or std::unique_ptr<std::thread>");
}

TEST_CASE("packetizer::Transport::setController uses RAII thread allocation") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/protocols/packetizer/Transport.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "Transport.cpp not found at " << path);

    const bool hasRaw = src.find("new std::thread") != std::string::npos;
    CHECK_MESSAGE(!hasRaw,
        " regression: raw 'new std::thread' is back in packetizer/Transport.cpp; "
        "fix replaced it with std::make_unique<std::thread>");

    CHECK_MESSAGE(threadIsRAII(src),
        "Transport.cpp must allocate worker thread via "
        "std::make_unique<std::thread> or std::unique_ptr<std::thread>");
}
