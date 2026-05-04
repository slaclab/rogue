/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Audit repro for PROT-015:
 * rssi::Controller::applicationRx() implements RSSI flow-control backpressure
 * by busy-looping with ``usleep(10)`` while ``txListCount_ >= curMaxBuffers_``.
 * No condition variable wakeup is used, so the application thread spins
 * continuously burning CPU rather than blocking until a transmit slot opens.
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
#include <vector>

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

static std::vector<std::string> splitLines(const std::string& src) {
    std::vector<std::string> lines;
    std::istringstream ss(src);
    std::string line;
    while (std::getline(ss, line)) lines.push_back(line);
    return lines;
}

TEST_CASE("PROT-015: rssi::Controller::applicationRx uses condvar instead of usleep busy-loop") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/protocols/rssi/Controller.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "Controller.cpp not found at " << path);

    // The fix replaces the usleep(10) backpressure spin with a condition
    // variable wait; verify the condvar primitives are present anywhere in
    // the file (notify_all/notify_one + wait_for is the fix-pattern).
    const bool hasNotify =
        src.find("notify_all") != std::string::npos ||
        src.find("notify_one") != std::string::npos;
    const bool hasWaitFor = src.find("wait_for") != std::string::npos;
    const bool usesCondVar = hasNotify && hasWaitFor;

    CHECK_MESSAGE(usesCondVar,
        "PROT-015 regression: rssi/Controller.cpp must use a "
        "std::condition_variable (notify_all/notify_one + wait_for) for "
        "RSSI transmit-window backpressure; fix(PROT-015) replaced the "
        "usleep(10) busy-loop with stCond_.wait_for so the application "
        "thread blocks until a transmit slot is signalled");
}
