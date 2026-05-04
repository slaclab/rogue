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

    // FIXED state: total_out_lo32 is not used (replaced with a 64-bit
    // calculation combining total_out_hi32 << 32 | total_out_lo32, or
    // using the bzip2 uint64_t extension API).
    const bool uses32bit = (src.find("total_out_lo32") != std::string::npos);
    CHECK_MESSAGE(!uses32bit,
                  "StreamZip::acceptFrame uses 32-bit "
                  "total_out_lo32; compressed output exceeding 4 GiB is "
                  "silently truncated without error; use 64-bit total_out");
}

TEST_CASE("StreamUnZip uses 32-bit total_out_lo32; truncates >4GiB") {
    const std::string src = readFile(
        ROGUE_SRC_DIR "/src/rogue/utilities/StreamUnZip.cpp");
    REQUIRE_MESSAGE(!src.empty(), "Could not read StreamUnZip.cpp");

    const bool uses32bit = (src.find("total_out_lo32") != std::string::npos);
    CHECK_MESSAGE(!uses32bit,
                  "StreamUnZip::acceptFrame uses 32-bit "
                  "total_out_lo32; decompressed output exceeding 4 GiB is "
                  "silently truncated; use 64-bit total_out");
}

TEST_CASE("StreamZip does not handle BZ_PARAM_ERROR") {
    const std::string src = readFile(
        ROGUE_SRC_DIR "/src/rogue/utilities/StreamZip.cpp");
    REQUIRE_MESSAGE(!src.empty(), "Could not read StreamZip.cpp");

    // FIXED state: BZ_PARAM_ERROR is explicitly checked in the bzip2
    // state machine so misaligned-buffer errors are caught and the
    // bzip2 stream is properly torn down.
    const bool handlesBzParamError =
        (src.find("BZ_PARAM_ERROR") != std::string::npos);
    CHECK_MESSAGE(handlesBzParamError,
                  "StreamZip state machine does not handle "
                  "BZ_PARAM_ERROR; BZ2_bzCompress returning BZ_PARAM_ERROR "
                  "is silently ignored, leaking bzip2 stream state on "
                  "misaligned buffer inputs");
}
