/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression tests
 * Both udp::Client and udp::Server allocate their worker thread via
 * ``new std::thread`` (with a try/catch guard), storing the result in a raw
 * ``thread_`` pointer.  The existing try/catch makes the immediate exception
 * path safe, but the raw-ptr pattern is still tech debt: future code changes
 * that add throw paths between allocation and the catch block re-introduce
 * the leak.  A correct fix replaces the raw pointer with
 * ``std::unique_ptr<std::thread>``.
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

/// Return true if the source uses RAII-managed thread allocation.
static bool hasRaiiThread(const std::string& src) {
    return src.find("make_unique<std::thread>") != std::string::npos ||
           src.find("unique_ptr<std::thread>") != std::string::npos;
}

TEST_CASE("udp::Client uses RAII thread allocation") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/protocols/udp/Client.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "Client.cpp not found at " << path);

    const bool hasRaw = src.find("new std::thread") != std::string::npos;
    CHECK_MESSAGE(!hasRaw,
        " regression: raw 'new std::thread' is back in udp/Client.cpp; "
        "fix replaced it with std::make_unique<std::thread>");

    CHECK_MESSAGE(hasRaiiThread(src),
        "Client.cpp must allocate worker thread via "
        "std::make_unique<std::thread> or std::unique_ptr<std::thread>");
}

TEST_CASE("udp::Server uses RAII thread allocation") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/protocols/udp/Server.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "Server.cpp not found at " << path);

    const bool hasRaw = src.find("new std::thread") != std::string::npos;
    CHECK_MESSAGE(!hasRaw,
        " regression: raw 'new std::thread' is back in udp/Server.cpp; "
        "fix replaced it with std::make_unique<std::thread>");

    CHECK_MESSAGE(hasRaiiThread(src),
        "Server.cpp must allocate worker thread via "
        "std::make_unique<std::thread> or std::unique_ptr<std::thread>");
}
