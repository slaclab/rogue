/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression tests
 * ControllerV1::transportRx() line 174 calls
 *   ``if (enSsi_ & (tmpLuser & 0x1)) tranFrame_[tmpDest]->setError(0x80)``
 * after the completed frame is extracted and ``tranFrame_[0]`` is reset to
 * null at line ~171.  For any ``tmpDest != 0`` the shared_ptr in
 * ``tranFrame_[tmpDest]`` was never initialised, so the ``->setError()``
 * call is an immediate null-dereference (UB / segfault).
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

TEST_CASE("ControllerV1::transportRx guards tranFrame_[tmpDest] before setError") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/protocols/packetizer/ControllerV1.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "ControllerV1.cpp not found at " << path);

    // setError(0x80) call must remain reachable in the file (it's part of the
    // SSI flow-control contract). The fix is to guard the call site against
    // tranFrame_[tmpDest] being a null shared_ptr.
    const int setErrorLine = findLine(src, "tranFrame_[tmpDest]->setError(0x80)");
    REQUIRE_MESSAGE(setErrorLine >= 0,
        "tranFrame_[tmpDest]->setError(0x80) not found in ControllerV1.cpp");

    // Search the 10 lines preceding setError AND the setError line itself —
    // the fix may inline the null check on the same line as the call
    // (e.g., 'if (tranFrame_[tmpDest]) tranFrame_[tmpDest]->setError(0x80);').
    const int searchStart = (setErrorLine > 10) ? setErrorLine - 10 : 0;
    const std::string ctx = extractLines(src, searchStart, setErrorLine - searchStart + 1);

    const bool hasNullCheck =
        ctx.find("if (tranFrame_[tmpDest])") != std::string::npos ||
        ctx.find("if (tranFrame_[tmpDest] !=") != std::string::npos ||
        ctx.find("assert(tranFrame_[tmpDest]") != std::string::npos;

    CHECK_MESSAGE(hasNullCheck,
        " regression: ControllerV1::transportRx calls setError(0x80) "
        "on tranFrame_[tmpDest] without a null guard; for any V1 frame with "
        "tmpDest != 0 the shared_ptr is null, causing a segfault. fix "
        "added an 'if (tranFrame_[tmpDest])' guard; if missing, the fix has "
        "regressed");
}
