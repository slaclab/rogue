/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression test for the V1 SSI-error path.
 *
 * The original code applied SSI errors after the completed frame had already
 * been pushed downstream and tranFrame_[0] reset, and on the WRONG index
 * (tranFrame_[tmpDest], which V1 never populates for tmpDest != 0).  That
 * produced two distinct bugs:
 *   1. for tmpDest != 0 the shared_ptr is null and ->setError() was an
 *      immediate null-dereference (UB / segfault), and
 *   2. for tmpDest == 0 the slot had already been reset, so the SSI
 *      indication was silently dropped.
 *
 * The fix applies setError(0x80) to the assembled frame (tranFrame_[0])
 * BEFORE pushing it downstream and BEFORE the reset.  This source-text test
 * locks that ordering in: setError(0x80) on tranFrame_[0] must precede the
 * pushFrame() call, and the wrong-index form must not reappear.
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

/// Locate the line number (0-based) of the first occurrence of needle.
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

/// Extract up to maxLines lines starting at startLine (0-based).
static std::string extractLines(const std::string& src, int startLine, int maxLines) {
    std::istringstream ss(src);
    std::string line;
    std::ostringstream out;
    int lineno = 0;
    int count  = 0;
    while (std::getline(ss, line) && count < maxLines) {
        if (lineno >= startLine) {
            out << line << "\n";
            ++count;
        }
        ++lineno;
    }
    return out.str();
}

TEST_CASE("ControllerV1::transportRx applies SSI error before push and reset") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/protocols/packetizer/ControllerV1.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "ControllerV1.cpp not found at " << path);

    // The wrong-index form must be gone.  It was both a null deref for
    // tmpDest != 0 and a no-op (after reset) for tmpDest == 0.
    const bool hasWrongIndex = src.find("tranFrame_[tmpDest]->setError") != std::string::npos;
    CHECK_MESSAGE(!hasWrongIndex,
        " regression: ControllerV1::transportRx still calls "
        "tranFrame_[tmpDest]->setError(...); V1 only populates tranFrame_[0], "
        "so this form is a null deref for tmpDest != 0 and a no-op (post-reset) "
        "for tmpDest == 0.  Apply setError on tranFrame_[0] BEFORE the push.");

    // Locate the setError(0x80) call on tranFrame_[0] and verify it appears
    // BEFORE the pushFrame() call in the EOF path.
    const int setErrorLine = findLine(src, "tranFrame_[0]->setError(0x80)");
    REQUIRE_MESSAGE(setErrorLine >= 0,
        "tranFrame_[0]->setError(0x80) not found in ControllerV1.cpp; "
        "the SSI error path must mark tranFrame_[0] before push/reset");

    const int pushLine = findLine(src, "app_[tranDest_]->pushFrame(tranFrame_[0])");
    REQUIRE_MESSAGE(pushLine >= 0,
        "app_[tranDest_]->pushFrame(tranFrame_[0]) not found in ControllerV1.cpp");

    CHECK_MESSAGE(setErrorLine < pushLine,
        " regression: ControllerV1::transportRx applies SSI "
        "setError(0x80) AFTER pushFrame()/reset; the marked error never "
        "reaches the application slave.  Move the setError call above the "
        "pushFrame call so the error indication ships with the frame.");
}
