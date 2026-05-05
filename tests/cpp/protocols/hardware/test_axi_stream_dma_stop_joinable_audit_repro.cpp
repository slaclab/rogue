/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression test for the AxiStreamDma::stop() joinability fix.
 * runThread() can now self-exit by setting threadEn_ = false and break-ing
 * out (e.g. when the in-loop fd_ guard fires).  If stop() gates all cleanup
 * behind 'if (threadEn_)' it will skip thread_->join() in that case, and
 * the unique_ptr<std::thread> destructor will call std::terminate() on the
 * still-joinable thread.  The fix is to drive cleanup from per-resource
 * state (thread joinability, desc_ presence, fd_ >= 0) rather than from
 * threadEn_, so stop() is correct on both the normal-stop and worker
 * self-exit paths and remains idempotent.
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

TEST_CASE("AxiStreamDma::stop joins via thread joinability, not threadEn_") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/hardware/axi/AxiStreamDma.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "AxiStreamDma.cpp not found at " << path);

    const std::string stopBody = extractFunctionBody(src, "rha::AxiStreamDma::stop(");
    REQUIRE_MESSAGE(!stopBody.empty(),
        "could not locate AxiStreamDma::stop body");

    // stop() must not gate cleanup behind 'if (threadEn_)' as a wrapper.
    // It is fine to assign threadEn_ = false unconditionally inside stop(),
    // but driving the join/cleanup off threadEn_ makes stop() skip join()
    // when runThread() has already set threadEn_ = false on its own.
    CHECK_MESSAGE(stopBody.find("if (threadEn_)") == std::string::npos,
        " regression: stop() must not gate cleanup behind 'if (threadEn_)'; "
        "runThread() can now set threadEn_ = false and exit on its own, in "
        "which case the join would be skipped and ~unique_ptr<std::thread> "
        "would call std::terminate() on the still-joinable thread");

    // Cleanup must be guarded by per-resource state.
    CHECK_MESSAGE(stopBody.find("joinable()") != std::string::npos,
        " regression: stop() must check thread_->joinable() so it joins on "
        "both the normal-stop path and the worker self-exit path");
}
