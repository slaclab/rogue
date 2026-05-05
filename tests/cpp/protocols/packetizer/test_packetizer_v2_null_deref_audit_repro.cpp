/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression test for the V2 SSI-error path.
 *
 * Mirrors the V1 audit-repro: the original ControllerV2::transportRx code
 * applied setError(0x80) to tranFrame_[tmpDest] AFTER the completed frame
 * had been pushed downstream and the slot reset to a null shared_ptr.  That
 * was both a null-dereference at runtime and a silent loss of the SSI
 * indication.  The fix moves the setError call ABOVE the push and reset,
 * so the error is on the assembled frame at the moment it is forwarded to
 * the application slave.  This source-text test locks that ordering in.
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

static int findLine(const std::string& src, const std::string& needle) {
    std::istringstream ss(src);
    std::string line;
    int lineno = 0;
    while (std::getline(ss, line)) {
        if (line.find(needle) != std::string::npos) return lineno;
        ++lineno;
    }
    return -1;
}

// Locate the first occurrence of needle on or after startLine (0-based).
static int findLineFrom(const std::string& src, const std::string& needle, int startLine) {
    std::istringstream ss(src);
    std::string line;
    int lineno = 0;
    while (std::getline(ss, line)) {
        if (lineno >= startLine && line.find(needle) != std::string::npos) return lineno;
        ++lineno;
    }
    return -1;
}

TEST_CASE("ControllerV2::transportRx applies SSI error before push and reset") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/protocols/packetizer/ControllerV2.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "ControllerV2.cpp not found at " << path);

    const int setErrorLine = findLine(src, "tranFrame_[tmpDest]->setError(0x80)");
    REQUIRE_MESSAGE(setErrorLine >= 0,
        "tranFrame_[tmpDest]->setError(0x80) not found in ControllerV2.cpp; "
        "the SSI error path must mark tranFrame_[tmpDest] before push/reset");

    // Earlier resets in this file are unrelated reassembly aborts on the
    // non-EOF path; we care about the post-EOF ordering, so look for the
    // push and reset that appear AFTER the setError site.
    const int pushLine = findLineFrom(src, "pushFrame(tranFrame_[tmpDest])", setErrorLine);
    REQUIRE_MESSAGE(pushLine >= 0,
        "pushFrame(tranFrame_[tmpDest]) following setError(0x80) not found in ControllerV2.cpp");

    const int resetLine = findLineFrom(src, "tranFrame_[tmpDest].reset()", setErrorLine);
    REQUIRE_MESSAGE(resetLine >= 0,
        "tranFrame_[tmpDest].reset() following setError(0x80) not found in ControllerV2.cpp");

    CHECK_MESSAGE(setErrorLine < pushLine,
        " regression: ControllerV2::transportRx applies SSI "
        "setError(0x80) AFTER pushFrame(); the marked error never reaches "
        "the application slave.  Move the setError call above the "
        "pushFrame call so the error indication ships with the frame.");

    CHECK_MESSAGE(setErrorLine < resetLine,
        " regression: ControllerV2::transportRx applies SSI "
        "setError(0x80) AFTER tranFrame_[tmpDest].reset(); the shared_ptr "
        "is null at that point and the call is an immediate null deref.");
}
