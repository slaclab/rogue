/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression tests for the AxiStreamDma openCount accounting fix.
 * AxiStreamDmaShared previously initialized openCount = 1 in its
 * constructor, and openShared() only incremented openCount on the
 * `fd != -1` branch.  An entry seeded by zeroCopyDisable() therefore
 * started at 1 with no real user, and additional AxiStreamDma instances
 * on that path bypassed the increment entirely while still triggering
 * a closeShared() decrement at destruction time.  Combined with an
 * unconditional ::close(desc->fd) inside closeShared(), this drove
 * openCount negative and called close(-1) (EBADF).
 * The fix is: openCount starts at 0, every successful openShared()
 * return path increments openCount exactly once, and closeShared()
 * skips ::close() when fd is -1.
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

TEST_CASE("AxiStreamDmaShared::AxiStreamDmaShared initializes openCount to 0") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/hardware/axi/AxiStreamDma.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "AxiStreamDma.cpp not found at " << path);

    const std::string ctorBody = extractFunctionBody(src, "rha::AxiStreamDmaShared::AxiStreamDmaShared(");
    REQUIRE_MESSAGE(!ctorBody.empty(),
        "could not locate AxiStreamDmaShared constructor body");

    CHECK_MESSAGE(ctorBody.find("openCount = 0") != std::string::npos,
        " regression: AxiStreamDmaShared must initialize openCount to 0; "
        "initializing to 1 pre-loads the refcount before any AxiStreamDma "
        "user exists and miscounts entries seeded by zeroCopyDisable()");
    CHECK_MESSAGE(ctorBody.find("openCount = 1") == std::string::npos,
        " regression: AxiStreamDmaShared ctor must not initialize openCount = 1");
}

TEST_CASE("AxiStreamDma::openShared increments openCount on every return path") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/hardware/axi/AxiStreamDma.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "AxiStreamDma.cpp not found at " << path);

    const std::string openBody = extractFunctionBody(src, "rha::AxiStreamDma::openShared(");
    REQUIRE_MESSAGE(!openBody.empty(),
        "could not locate AxiStreamDma::openShared body");

    // closeShared() unconditionally decrements openCount, so each successful
    // openShared() path must increment it.  Three return paths exist:
    // (1) existing entry already opened (fd != -1)
    // (2) existing entry zero-copy-disabled (zCopyEn == false, fd == -1)
    // (3) new entry / re-open path that runs ::open + dmaMapDma
    // We can't structurally count "return paths", but we can require that
    // openShared has at least three openCount++ statements - one per branch.
    size_t pos       = 0;
    int incrementCnt = 0;
    while ((pos = openBody.find("openCount++", pos)) != std::string::npos) {
        ++incrementCnt;
        ++pos;
    }
    CHECK_MESSAGE(incrementCnt >= 3,
        " regression: openShared() must increment openCount on every successful "
        "return (existing-open, existing-zero-copy-disabled, and freshly "
        "opened branches); found "
        << incrementCnt << " openCount++ sites, expected >= 3");
}

TEST_CASE("AxiStreamDma::closeShared guards ::close against fd == -1") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/hardware/axi/AxiStreamDma.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "AxiStreamDma.cpp not found at " << path);

    const std::string closeBody = extractFunctionBody(src, "rha::AxiStreamDma::closeShared(");
    REQUIRE_MESSAGE(!closeBody.empty(),
        "could not locate AxiStreamDma::closeShared body");

    // The zeroCopyDisable() flow leaves desc->fd == -1 for the lifetime of
    // the entry, so closeShared() must not call ::close(desc->fd) without a
    // != -1 guard.  Strip C++ '//' comments before scanning so the comment
    // explaining the guard isn't mistaken for the call site, then walk every
    // ::close(desc->fd) occurrence and require each one is preceded by an
    // 'if (desc->fd != -1)' guard.
    std::string code;
    code.reserve(closeBody.size());
    for (size_t i = 0; i < closeBody.size();) {
        if (i + 1 < closeBody.size() && closeBody[i] == '/' && closeBody[i + 1] == '/') {
            while (i < closeBody.size() && closeBody[i] != '\n') ++i;
        } else {
            code.push_back(closeBody[i]);
            ++i;
        }
    }

    size_t closePos = code.find("::close(desc->fd)");
    REQUIRE_MESSAGE(closePos != std::string::npos,
        "could not locate ::close(desc->fd) in closeShared body (after stripping comments)");

    bool everyCloseGuarded = true;
    while (closePos != std::string::npos) {
        const std::string prefix = code.substr(0, closePos);
        const bool guarded =
            prefix.rfind("if (desc->fd != -1)") != std::string::npos ||
            prefix.rfind("if (desc->fd >= 0)")  != std::string::npos;
        if (!guarded) {
            everyCloseGuarded = false;
            break;
        }
        closePos = code.find("::close(desc->fd)", closePos + 1);
    }
    CHECK_MESSAGE(everyCloseGuarded,
        " regression: closeShared() must guard ::close(desc->fd) with an "
        "'if (desc->fd != -1)' check (zeroCopyDisable() leaves fd == -1, so "
        "an unconditional ::close issues close(-1) and returns EBADF)");
}
