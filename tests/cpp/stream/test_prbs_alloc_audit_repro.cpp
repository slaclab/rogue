/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression tests for Prbs raw-resource ownership bugs:
 *   Prbs ctor malloc(taps_) result not checked for NULL
 *   setTaps() free+malloc; no NULL guard before taps_[i] writes
 *   enable() allocates txThread_ with raw ``new std::thread``
 *
 * Source-text invariant tests on Prbs.cpp.  On HEAD all three fixes are
 * absent -> CHECK_MESSAGE fires for each.
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

TEST_CASE("Prbs ctor malloc(taps_) not checked for NULL") {
    const std::string src = readFile(
        ROGUE_SRC_DIR "/src/rogue/utilities/Prbs.cpp");
    REQUIRE_MESSAGE(!src.empty(), "Could not read Prbs.cpp");

    // Locate the ctor malloc call for taps_
    const std::string sentinel = "taps_    = reinterpret_cast<uint8_t*>(malloc(";
    const std::size_t pos = src.find(sentinel);
    // Also try alternate whitespace
    const std::size_t pos2 = src.find("taps_ = reinterpret_cast<uint8_t*>(malloc(");
    const std::size_t mallocPos = (pos != std::string::npos) ? pos : pos2;
    REQUIRE_MESSAGE(mallocPos != std::string::npos,
                    "Could not locate taps_ malloc in Prbs ctor");

    // Extract the 200 bytes after the malloc for NULL check
    const std::string window = src.substr(mallocPos, 200);

    const bool hasNullCheck = (
        window.find("== NULL") != std::string::npos ||
        window.find("!= NULL") != std::string::npos ||
        window.find("nullptr") != std::string::npos ||
        window.find("make_unique") != std::string::npos);

    CHECK_MESSAGE(hasNullCheck,
                  "Prbs ctor allocates taps_ with malloc but does "
                  "not check the return value for NULL; a failed allocation "
                  "is silently followed by taps_[0..3] writes -> crash");
}

TEST_CASE("setTaps() free+malloc no NULL guard before taps_[i] write") {
    const std::string src = readFile(
        ROGUE_SRC_DIR "/src/rogue/utilities/Prbs.cpp");
    REQUIRE_MESSAGE(!src.empty(), "Could not read Prbs.cpp");

    // Locate setTaps implementation
    const std::size_t setTapsPos = src.find("Prbs::setTaps(");
    REQUIRE_MESSAGE(setTapsPos != std::string::npos,
                    "Could not locate Prbs::setTaps in Prbs.cpp");

    // Extract the setTaps body (500 bytes)
    const std::string region = src.substr(setTapsPos, 500);

    // FIXED state: after the malloc call in setTaps, there is a NULL check
    // before the taps_[i] write loop.
    const bool hasMalloc = (region.find("malloc(") != std::string::npos);
    if (!hasMalloc) {
        // Already fixed (using vector/unique_ptr) - test passes
        return;
    }

    // malloc present; check for NULL guard
    const std::size_t mallocPos = region.find("malloc(");
    const std::string afterMalloc = region.substr(mallocPos, 200);

    const bool hasNullCheck = (
        afterMalloc.find("== NULL") != std::string::npos ||
        afterMalloc.find("!= NULL") != std::string::npos ||
        afterMalloc.find("nullptr") != std::string::npos);

    CHECK_MESSAGE(hasNullCheck,
                  "Prbs::setTaps() free(taps_) then malloc with no "
                  "NULL guard before taps_[i] writes; NULL return -> crash on "
                  "write to taps_[0]");
}

TEST_CASE("Prbs::enable() uses raw new std::thread for txThread_") {
    const std::string src = readFile(
        ROGUE_SRC_DIR "/src/rogue/utilities/Prbs.cpp");
    REQUIRE_MESSAGE(!src.empty(), "Could not read Prbs.cpp");

    // Locate the enable() function
    const std::size_t enablePos = src.find("Prbs::enable(");
    REQUIRE_MESSAGE(enablePos != std::string::npos,
                    "Could not locate Prbs::enable in Prbs.cpp");

    // Extract the enable() body (300 bytes)
    const std::string region = src.substr(enablePos, 300);

    // FIXED state: txThread_ uses std::unique_ptr<std::thread> instead of
    // raw "new std::thread"
    const bool hasRawNew = (region.find("new std::thread") != std::string::npos);
    CHECK_MESSAGE(!hasRawNew,
                  "Prbs::enable() allocates txThread_ with raw "
                  "new std::thread; disable() does delete txThread_; should "
                  "use std::unique_ptr<std::thread> for automatic cleanup");
}
