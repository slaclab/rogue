/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression tests for bzip2 output truncation and state-machine swallow bugs:
 *   StreamZip uses 32-bit total_out_lo32; truncates output >4GiB
 *   StreamUnZip uses 32-bit total_out_lo32; same truncation risk
 *   StreamZip state machine only checks BZ_SEQUENCE_ERROR;
 *             BZ_PARAM_ERROR is not caught, leaking bzip2 state
 *
 * Source-text invariant tests; each TEST_CASE asserts a structural property
 * that the fixed code must satisfy.  On HEAD the fixes are absent.
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

TEST_CASE("StreamZip uses 32-bit total_out_lo32; truncates >4GiB") {
    const std::string src = readFile(
        ROGUE_SRC_DIR "/src/rogue/utilities/StreamZip.cpp");
    REQUIRE_MESSAGE(!src.empty(), "Could not read StreamZip.cpp");

    // FIXED state has two valid forms:
    //   (a) total_out_lo32 dropped entirely (manual uint64_t accumulator,
    //       or the bzip2 64-bit extension API).
    //   (b) total_out_hi32 << 32 | total_out_lo32 combined into a 64-bit
    //       value; both tokens present.
    const bool hasLo32      = (src.find("total_out_lo32") != std::string::npos);
    const bool hasHi32      = (src.find("total_out_hi32") != std::string::npos);
    // doctest forbids || inside CHECK_MESSAGE; precompute the disjunction.
    const bool isFixed = (!hasLo32) || hasHi32;
    CHECK_MESSAGE(isFixed,
                  "StreamZip::acceptFrame uses 32-bit total_out_lo32 in "
                  "isolation; compressed output exceeding 4 GiB is silently "
                  "truncated.  Either drop total_out_lo32 or pair it with "
                  "total_out_hi32 to assemble a 64-bit total_out.");
}

TEST_CASE("StreamUnZip uses 32-bit total_out_lo32; truncates >4GiB") {
    const std::string src = readFile(
        ROGUE_SRC_DIR "/src/rogue/utilities/StreamUnZip.cpp");
    REQUIRE_MESSAGE(!src.empty(), "Could not read StreamUnZip.cpp");

    const bool hasLo32 = (src.find("total_out_lo32") != std::string::npos);
    const bool hasHi32 = (src.find("total_out_hi32") != std::string::npos);
    const bool isFixed = (!hasLo32) || hasHi32;
    CHECK_MESSAGE(isFixed,
                  "StreamUnZip::acceptFrame uses 32-bit total_out_lo32 in "
                  "isolation; decompressed output exceeding 4 GiB is silently "
                  "truncated.  Either drop total_out_lo32 or pair it with "
                  "total_out_hi32 to assemble a 64-bit total_out.");
}

TEST_CASE("StreamZip does not handle BZ_PARAM_ERROR") {
    const std::string src = readFile(
        ROGUE_SRC_DIR "/src/rogue/utilities/StreamZip.cpp");
    REQUIRE_MESSAGE(!src.empty(), "Could not read StreamZip.cpp");

    // FIXED state has two valid forms:
    //   (a) BZ_PARAM_ERROR named explicitly in the state machine.
    //   (b) Generic negative-code check (`ret < 0`).  All bzip2 errors are
    //       negative; this is the canonical generic guard.
    const bool namesBzParamError =
        (src.find("BZ_PARAM_ERROR") != std::string::npos);
    const bool catchesNegativeRet = (src.find("ret < 0") != std::string::npos);
    const bool handlesMoreCodes   = namesBzParamError || catchesNegativeRet;
    CHECK_MESSAGE(handlesMoreCodes,
                  "StreamZip does not catch BZ2_bzCompress error codes beyond "
                  "BZ_SEQUENCE_ERROR; can leak bzip2 state on misaligned "
                  "buffers.  Either name BZ_PARAM_ERROR explicitly or use a "
                  "generic negative-return-code check (ret < 0) together with "
                  "cleanup.");
}
