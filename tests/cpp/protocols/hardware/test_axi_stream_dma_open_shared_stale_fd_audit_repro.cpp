/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression test for the AxiStreamDma::openShared() stale-fd fix.
 *
 * closeShared() resets desc->fd to -1 (along with bCount/bSize/rawBuff) when
 * openCount drops to 0, but it does NOT erase the entry from sharedBuffers_;
 * the entry is a long-lived per-path cache.  When a later AxiStreamDma is
 * constructed for the same path, openShared() finds the entry, observes
 * fd == -1 with zCopyEn == true, and falls through to the open + map
 * branch.  If ::open succeeds but a subsequent step (driver version checks,
 * dmaCheckVersion, dmaMapDma) fails, the original code called
 * ::close(ret->fd) and threw without resetting ret->fd back to -1.  Because
 * the underlying AxiStreamDmaShared instance is the persistent map entry,
 * the next caller would hit the "ret->fd != -1" fast-path, increment
 * openCount, and reuse a closed file descriptor.
 *
 * The fix is: every error path in openShared() that calls ::close(ret->fd)
 * must also set ret->fd = -1 (and reset partial mapping state) before
 * throwing, so the persistent shared-buffer record is left in a clean
 * "fd == -1" state.
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

// Extract the body of a member function definition.  Returns the substring
// from the opening '{' of the matching definition to the matching '}'.
// Returns "" if the function or its braces cannot be located.
static std::string extractFunctionBody(const std::string& src, const std::string& signaturePrefix) {
    const size_t sigPos = src.find(signaturePrefix);
    if (sigPos == std::string::npos) return "";
    const size_t openBrace = src.find('{', sigPos);
    if (openBrace == std::string::npos) return "";
    int depth = 0;
    for (size_t i = openBrace; i < src.size(); ++i) {
        if (src[i] == '{') {
            ++depth;
        } else if (src[i] == '}') {
            --depth;
            if (depth == 0) return src.substr(openBrace, i - openBrace + 1);
        }
    }
    return "";
}

// Strip C++ '//' line comments from src.  Used so explanatory comments
// referencing 'ret->fd = -1' don't satisfy structural checks.
static std::string stripLineComments(const std::string& src) {
    std::string out;
    out.reserve(src.size());
    for (size_t i = 0; i < src.size();) {
        if (i + 1 < src.size() && src[i] == '/' && src[i + 1] == '/') {
            while (i < src.size() && src[i] != '\n') ++i;
        } else {
            out.push_back(src[i]);
            ++i;
        }
    }
    return out;
}

// Collapse runs of whitespace (space + tab) into a single space so structural
// checks aren't sensitive to the surrounding code's column-alignment style
// (e.g., 'ret->fd      = -1' written for visual alignment with sibling
// resets like 'ret->bCount  = 0').
static std::string collapseSpaces(const std::string& src) {
    std::string out;
    out.reserve(src.size());
    bool prevSpace = false;
    for (char c : src) {
        if (c == ' ' || c == '\t') {
            if (!prevSpace) out.push_back(' ');
            prevSpace = true;
        } else {
            out.push_back(c);
            prevSpace = false;
        }
    }
    return out;
}

TEST_CASE("AxiStreamDma::openShared resets ret->fd to -1 on every error path") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/hardware/axi/AxiStreamDma.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "AxiStreamDma.cpp not found at " << path);

    const std::string openBody = extractFunctionBody(src, "rha::AxiStreamDma::openShared(");
    REQUIRE_MESSAGE(!openBody.empty(),
        "could not locate AxiStreamDma::openShared body");

    const std::string code = collapseSpaces(stripLineComments(openBody));

    // Walk every '::close(ret->fd)' occurrence inside openShared() and
    // require that 'ret->fd = -1' appears between the close call and the
    // next throw.  The shared record persists in sharedBuffers_ across
    // openCount==0 cycles, so leaving ret->fd != -1 after closing the
    // descriptor would let a future caller reuse a stale, closed fd via the
    // 'ret->fd != -1' fast-path at the top of openShared().
    size_t closePos       = code.find("::close(ret->fd)");
    REQUIRE_MESSAGE(closePos != std::string::npos,
        "expected at least one ::close(ret->fd) in openShared (driver/version/map error paths)");

    int closeSites           = 0;
    bool everyCloseFollowed  = true;
    while (closePos != std::string::npos) {
        ++closeSites;
        const size_t throwPos = code.find("throw", closePos);
        REQUIRE_MESSAGE(throwPos != std::string::npos,
            "::close(ret->fd) at offset " << closePos << " is not followed by a throw in openShared");
        const std::string between = code.substr(closePos, throwPos - closePos);
        if (between.find("ret->fd = -1") == std::string::npos) {
            everyCloseFollowed = false;
            break;
        }
        closePos = code.find("::close(ret->fd)", closePos + 1);
    }

    CHECK_MESSAGE(closeSites >= 3,
        " regression: openShared() should ::close(ret->fd) on each of the three "
        "error paths (api version, driver check, dmaMapDma); found "
        << closeSites << " close sites");
    CHECK_MESSAGE(everyCloseFollowed,
        " regression: every ::close(ret->fd) error path in openShared() must "
        "set ret->fd = -1 before throwing.  closeShared() leaves the entry in "
        "sharedBuffers_ after openCount drops to 0, so a non-(-1) fd left in "
        "the persistent record would be reused as a stale, closed descriptor "
        "by the next openShared() caller hitting the 'ret->fd != -1' fast-path.");
}

TEST_CASE("AxiStreamDma::openShared scrubs partial mapping state on dmaMapDma failure") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/hardware/axi/AxiStreamDma.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "AxiStreamDma.cpp not found at " << path);

    const std::string openBody = extractFunctionBody(src, "rha::AxiStreamDma::openShared(");
    REQUIRE_MESSAGE(!openBody.empty(),
        "could not locate AxiStreamDma::openShared body");

    const std::string code = collapseSpaces(stripLineComments(openBody));

    // Locate the rawBuff == NULL error block; require the cleanup before the
    // throw resets bCount, bSize, and rawBuff in addition to fd.  dmaMapDma
    // can write to bCount/bSize even on failure, so leaving those values in
    // the persistent shared record would mislead the next caller.
    const size_t failPos = code.find("ret->rawBuff == NULL");
    REQUIRE_MESSAGE(failPos != std::string::npos,
        "expected an 'ret->rawBuff == NULL' check in openShared()");
    const size_t throwPos = code.find("throw", failPos);
    REQUIRE_MESSAGE(throwPos != std::string::npos,
        "expected a throw after the 'ret->rawBuff == NULL' check in openShared()");
    const std::string block = code.substr(failPos, throwPos - failPos);

    const bool bCountReset  = block.find("ret->bCount = 0") != std::string::npos;
    const bool bSizeReset   = block.find("ret->bSize = 0") != std::string::npos;
    const bool rawBuffReset = block.find("ret->rawBuff = NULL") != std::string::npos;

    CHECK_MESSAGE(bCountReset,
        " regression: openShared() must reset ret->bCount = 0 before throwing on "
        "dmaMapDma failure (the persistent shared record otherwise carries a stale "
        "buffer count to the next caller)");
    CHECK_MESSAGE(bSizeReset,
        " regression: openShared() must reset ret->bSize = 0 before throwing on "
        "dmaMapDma failure");
    CHECK_MESSAGE(rawBuffReset,
        " regression: openShared() must reset ret->rawBuff = NULL before throwing "
        "on dmaMapDma failure (defensive: dmaMapDma should leave it NULL on "
        "failure, but the cleanup must not depend on that)");
}
