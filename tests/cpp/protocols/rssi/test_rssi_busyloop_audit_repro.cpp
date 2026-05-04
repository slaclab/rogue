/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression tests
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

TEST_CASE("rssi::Controller has no usleep busy-loop in applicationRx backpressure") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/protocols/rssi/Controller.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "Controller.cpp not found at " << path);

    // The bug was a `while (txListCount_ >= curMaxBuffers_) { usleep(10);... }`
    // CPU-burning spin in applicationRx().  The fix replaced it with
    // stCond_.wait_for under stMtx_.  No other usleep() call exists in this
    // file, so the absence of `usleep(` is a strict regression guard.
    const bool hasUsleep = src.find("usleep(") != std::string::npos;
    CHECK_MESSAGE(!hasUsleep,
        " regression: usleep() reintroduced in rssi/Controller.cpp; "
        "the fix replaced the applicationRx() busy-loop with a "
        "std::condition_variable wait_for under stMtx_, so the application "
        "thread blocks until a transmit slot is signalled rather than "
        "spinning every 10 us");
}
