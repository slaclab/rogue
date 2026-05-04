/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression tests
 * rssi::Application::setController() and rssi::Controller::start() allocate
 * worker threads via ``new std::thread`` without any try/catch guard.  If the
 * thread constructor throws (OOM), the raw thread_ pointer is left dangling
 * and the later stop()/destructor call dereferences it.
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
static bool hasRaiiThread(const std::string& src) {
    return src.find("make_unique<std::thread>") != std::string::npos ||
           src.find("unique_ptr<std::thread>") != std::string::npos;
}

TEST_CASE("rssi::Application::setController uses RAII thread allocation") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/protocols/rssi/Application.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "Application.cpp not found at " << path);

    const bool hasRaw = src.find("new std::thread") != std::string::npos;
    CHECK_MESSAGE(!hasRaw,
        " regression: raw 'new std::thread' is back in rssi/Application.cpp; "
        "fix replaced it with std::make_unique<std::thread>");

    CHECK_MESSAGE(hasRaiiThread(src),
        "rssi/Application.cpp must allocate worker thread via "
        "std::make_unique<std::thread> or std::unique_ptr<std::thread>");
}

TEST_CASE("rssi::Controller::start uses RAII thread allocation") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/protocols/rssi/Controller.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "Controller.cpp not found at " << path);

    const bool hasRaw = src.find("new std::thread") != std::string::npos;
    CHECK_MESSAGE(!hasRaw,
        " regression: raw 'new std::thread' is back in rssi/Controller.cpp; "
        "fix replaced it with std::make_unique<std::thread>");

    CHECK_MESSAGE(hasRaiiThread(src),
        "rssi/Controller.cpp must allocate worker thread via "
        "std::make_unique<std::thread> or std::unique_ptr<std::thread>");
}
