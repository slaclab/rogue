/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression tests for numeric edge-case UB in Block floating-point/fixed-point
 * conversion methods:
 *   setFloat8 lacks an explicit NaN/Inf early-return guard
 *   setFixed intermediate round() result can be +INF before
 *             static_cast<int64_t> -> UB
 *   setUFixed same root cause as  for unsigned path
 *
 * Each TEST_CASE is a source-text invariant check on Block.cpp.
 * On HEAD the guards are absent -> CHECK_MESSAGE fires.
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

// Extract the source region for a named function body.
// Finds the function header and returns the next 'windowBytes' characters.
static std::string functionRegion(const std::string& src,
                                  const std::string& funcName,
                                  std::size_t windowBytes = 1000) {
    const std::size_t pos = src.find(funcName);
    if (pos == std::string::npos) return std::string();
    return src.substr(pos, windowBytes);
}

TEST_CASE("setFloat8 lacks NaN/Inf early-return guard") {
    const std::string src = readFile(
        ROGUE_SRC_DIR "/src/rogue/interfaces/memory/Block.cpp");
    REQUIRE_MESSAGE(!src.empty(), "Could not read Block.cpp");

    // The setFloat8 function (not the Python wrapper) begins at the
    // "void rim::Block::setFloat8(const float& val," declaration.
    const std::string region = functionRegion(
        src, "void rim::Block::setFloat8(const float&");
    REQUIRE_MESSAGE(!region.empty(),
                    "Could not locate setFloat8 implementation in Block.cpp");

    // FIXED state: an isnan/isinf/isfinite guard before the conversion.
    const bool hasGuard = (
        region.find("isnan(") != std::string::npos  ||
        region.find("isinf(") != std::string::npos  ||
        region.find("isfinite(") != std::string::npos ||
        region.find("std::isnan") != std::string::npos ||
        region.find("std::isinf") != std::string::npos ||
        region.find("std::isfinite") != std::string::npos);
    CHECK_MESSAGE(hasGuard,
                  "Block::setFloat8 lacks explicit NaN/Inf early-"
                  "return guard; NaN/Inf inputs silently produce wrong E4M3 "
                  "encoding without alerting the caller");
}

TEST_CASE("setFixed round() -> static_cast<int64_t> UB for +INF") {
    const std::string src = readFile(
        ROGUE_SRC_DIR "/src/rogue/interfaces/memory/Block.cpp");
    REQUIRE_MESSAGE(!src.empty(), "Could not read Block.cpp");

    const std::string region = functionRegion(
        src, "void rim::Block::setFixed(const double&");
    REQUIRE_MESSAGE(!region.empty(),
                    "Could not locate setFixed implementation in Block.cpp");

    // FIXED state: an isfinite/isinf guard before the round() -> cast step.
    const bool hasGuard = (
        region.find("isfinite(") != std::string::npos  ||
        region.find("isinf(") != std::string::npos     ||
        region.find("isnan(") != std::string::npos     ||
        region.find("std::isfinite") != std::string::npos ||
        region.find("std::isinf") != std::string::npos);
    CHECK_MESSAGE(hasGuard,
                  "Block::setFixed round(val*pow(2,binPoint_)) can "
                  "produce +INF before static_cast<int64_t> -> UB; needs "
                  "std::isfinite guard before the round/cast step");
}

TEST_CASE("setUFixed round() -> static_cast<uint64_t> UB") {
    const std::string src = readFile(
        ROGUE_SRC_DIR "/src/rogue/interfaces/memory/Block.cpp");
    REQUIRE_MESSAGE(!src.empty(), "Could not read Block.cpp");

    const std::string region = functionRegion(
        src, "void rim::Block::setUFixed(const double&");
    REQUIRE_MESSAGE(!region.empty(),
                    "Could not locate setUFixed implementation in Block.cpp");

    // FIXED state: an isfinite/isinf guard before the round() -> cast step.
    const bool hasGuard = (
        region.find("isfinite(") != std::string::npos  ||
        region.find("isinf(") != std::string::npos     ||
        region.find("isnan(") != std::string::npos     ||
        region.find("std::isfinite") != std::string::npos ||
        region.find("std::isinf") != std::string::npos);
    CHECK_MESSAGE(hasGuard,
                  "Block::setUFixed round(val*pow(2,binPoint_)) "
                  "can produce +INF before static_cast<uint64_t> -> UB; needs "
                  "std::isfinite guard before the round/cast step");
}
