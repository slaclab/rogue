/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Audit repros for HW-004, HW-005, HW-006:
 * Three FD_SET sites in AxiStreamDma.cpp (acceptReq, acceptFrame, runThread)
 * call FD_SET(fd_, &fds) without first checking fd_ < FD_SETSIZE.  On Linux
 * FD_SETSIZE=1024; if the DMA device fd_ reaches >= 1024 the FD_SET macro
 * silently writes past the fd_set bitset, causing heap corruption.
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

/// Return the 0-based line index of the Nth occurrence of needle.
static int findNthLine(const std::vector<std::string>& lines,
                       const std::string& needle,
                       unsigned occurrence) {
    unsigned count = 0;
    for (int i = 0; i < static_cast<int>(lines.size()); ++i) {
        if (lines[i].find(needle) != std::string::npos) {
            if (count == occurrence) return i;
            ++count;
        }
    }
    return -1;
}

/// Return true if a FD_SETSIZE guard precedes the FD_SET call within 8 lines.
static bool hasFdGuard(const std::vector<std::string>& lines, int fdSetLine) {
    const int start = (fdSetLine > 8) ? fdSetLine - 8 : 0;
    for (int i = start; i < fdSetLine; ++i) {
        if (lines[i].find("FD_SETSIZE") != std::string::npos) return true;
    }
    return false;
}

/// Return true if `line` is a single-line comment (`// ...` after optional
/// whitespace). Used to skip FD_SET tokens that appear only in comments.
static bool isCommentLine(const std::string& line) {
    for (char c : line) {
        if (c == ' ' || c == '\t') continue;
        return c == '/' && line.find("//") != std::string::npos &&
               line.find("//") <= line.find("FD_SET");
    }
    return false;
}

/// Return true if every active (non-comment) FD_SET(fd_, ...) call in the
/// file has an FD_SETSIZE guard within the 8 lines preceding it.
static bool everyFdSetIsGuarded(const std::vector<std::string>& lines) {
    bool allGuarded = true;
    bool any        = false;
    for (int i = 0; i < static_cast<int>(lines.size()); ++i) {
        if (lines[i].find("FD_SET(fd_") == std::string::npos) continue;
        if (isCommentLine(lines[i])) continue;
        any = true;
        if (!hasFdGuard(lines, i)) allGuarded = false;
    }
    return any && allGuarded;
}

TEST_CASE("HW-004/005/006: AxiStreamDma all FD_SET sites guarded by FD_SETSIZE") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/hardware/axi/AxiStreamDma.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "AxiStreamDma.cpp not found at " << path);

    const auto lines = splitLines(src);
    CHECK_MESSAGE(everyFdSetIsGuarded(lines),
        "HW-004/005/006 regression: at least one FD_SET(fd_, ...) site in "
        "hardware/axi/AxiStreamDma.cpp (acceptReq/acceptFrame/runThread) lacks "
        "an FD_SETSIZE bounds check within the preceding 8 lines; fix(HW-004..006) "
        "added 'if (fd_ >= FD_SETSIZE) throw ...' before each FD_SET to prevent "
        "heap corruption when fd_ >= 1024");
}
