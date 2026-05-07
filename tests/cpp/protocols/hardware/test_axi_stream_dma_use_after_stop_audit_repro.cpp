/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression test for the AxiStreamDma use-after-stop guard.
 * stop() resets desc_ (to break the closeShared() double-decrement and
 * release the shared descriptor) and clears fd_ to -1.  acceptReq()
 * dereferences desc_->bSize at the very top of its body, so a post-stop
 * acceptReq() would segfault on the null shared_ptr instead of throwing
 * a clean GeneralError.  acceptFrame() does not dereference desc_ but
 * still uses fd_ in select()/dmaWrite() and only catches an invalid fd_
 * deep inside the inner write loop, after frame->lock() and buffer
 * iteration have already run.  Both methods must fail-fast at entry when
 * the instance has been stopped or did not finish construction.
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

// Strip C++ line comments (// ... \n) so structural scans don't trip on
// `desc_->` or `!desc_` tokens that appear only inside human-prose comments.
// Block comments are out of scope for this audit; the source uses only line
// comments at the relevant sites.
static std::string stripLineComments(const std::string& src) {
    std::string out;
    out.reserve(src.size());
    bool inComment = false;
    for (size_t i = 0; i < src.size(); ++i) {
        if (!inComment && i + 1 < src.size() && src[i] == '/' && src[i + 1] == '/') {
            inComment = true;
            ++i;  // skip second '/'
            continue;
        }
        if (inComment) {
            if (src[i] == '\n') {
                inComment = false;
                out.push_back('\n');
            }
            continue;
        }
        out.push_back(src[i]);
    }
    return out;
}

// Returns true if `body` contains a guard that throws on a null/invalid
// state at entry (before any desc_-> dereference).  The guard must appear
// before the first `desc_->` dereference in the body to count.  Comments
// are stripped first so prose mentioning desc_ doesn't fool the scan.
static bool hasEntryGuardBeforeDescDeref(const std::string& body) {
    const std::string code = stripLineComments(body);
    const size_t guardPos  = code.find("!desc_");
    if (guardPos == std::string::npos) return false;
    const size_t derefPos = code.find("desc_->");
    if (derefPos == std::string::npos) return true;  // no deref, guard alone is fine
    return guardPos < derefPos;
}

TEST_CASE("AxiStreamDma::acceptReq guards against use-after-stop") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/hardware/axi/AxiStreamDma.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "AxiStreamDma.cpp not found at " << path);

    const std::string body = extractFunctionBody(src, "rha::AxiStreamDma::acceptReq(");
    REQUIRE_MESSAGE(!body.empty(),
        "could not locate AxiStreamDma::acceptReq body");

    // acceptReq() must check !desc_ (and ideally fd_ < 0) before the first
    // desc_->bSize dereference, otherwise a post-stop call segfaults.
    CHECK_MESSAGE(hasEntryGuardBeforeDescDeref(body),
        " regression: AxiStreamDma::acceptReq() must guard '!desc_' before "
        "the first 'desc_->' dereference; stop() resets desc_ to nullptr, so "
        "without this guard a post-stop acceptReq() segfaults on desc_->bSize "
        "instead of throwing a clean GeneralError");
}

TEST_CASE("AxiStreamDma::acceptFrame guards against use-after-stop") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/hardware/axi/AxiStreamDma.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "AxiStreamDma.cpp not found at " << path);

    const std::string body = extractFunctionBody(src, "rha::AxiStreamDma::acceptFrame(");
    REQUIRE_MESSAGE(!body.empty(),
        "could not locate AxiStreamDma::acceptFrame body");

    // acceptFrame() does not dereference desc_, but it does use fd_ in select()
    // and dmaWrite()/dmaWriteIndex(); a post-stop call should fail-fast at
    // entry rather than running frame->lock() + buffer iteration only to
    // throw deep inside the inner write loop.  Strip line comments so prose
    // mentioning these tokens doesn't satisfy the scan.
    const std::string code  = stripLineComments(body);
    const bool hasDescGuard = code.find("!desc_") != std::string::npos;
    const bool hasFdGuard   = code.find("fd_ < 0") != std::string::npos;
    CHECK_MESSAGE(hasDescGuard,
        " regression: AxiStreamDma::acceptFrame() must guard '!desc_' at entry "
        "so a post-stop call fails fast with a clean GeneralError instead of "
        "doing wasted setup work before the inner-loop FD_SETSIZE guard fires");
    CHECK_MESSAGE(hasFdGuard,
        " regression: AxiStreamDma::acceptFrame() must guard 'fd_ < 0' at entry "
        "so a post-stop call fails fast with a clean GeneralError instead of "
        "doing wasted setup work before the inner-loop FD_SETSIZE guard fires");
}
