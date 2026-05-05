/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression tests
 * AxiStreamDma.cpp declares ``sharedBuffers_`` as a file-scope static
 * std::map at line ~45.  openShared() (called from the constructor) and
 * closeShared() (called from the destructor) access this map without any
 * mutex protection.  Concurrent construction of two AxiStreamDma objects
 * on separate threads races on the static map, potentially corrupting it.
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

TEST_CASE("AxiStreamDma sharedBuffers_ static map accessed without mutex") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/hardware/axi/AxiStreamDma.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "AxiStreamDma.cpp not found at " << path);

    // Confirm the static sharedBuffers_ map exists
    REQUIRE_MESSAGE(src.find("sharedBuffers_") != std::string::npos,
        "sharedBuffers_ not found in AxiStreamDma.cpp; file may have changed");

    // A static mutex must be declared in this translation unit to guard sharedBuffers_.
    const bool hasMutexDecl =
        src.find("sharedBuffersMtx") != std::string::npos ||
        src.find("sharedMtx") != std::string::npos ||
        src.find("sharedBuffers_Mtx") != std::string::npos ||
        src.find("static std::mutex") != std::string::npos;
    REQUIRE_MESSAGE(hasMutexDecl,
        " regression: AxiStreamDma must declare a static std::mutex "
        "(e.g. sharedBuffersMtx) protecting the file-scope sharedBuffers_ map");

    // Both openShared() and closeShared() must actually take a lock_guard
    // (or unique_lock) on a std::mutex inside their bodies, otherwise the
    // declared mutex is dead code and the race remains.  Locating each
    // function body and grepping inside it catches that, where a flat
    // file-wide scan does not.
    const std::string openBody  = extractFunctionBody(src, "rha::AxiStreamDma::openShared(");
    const std::string closeBody = extractFunctionBody(src, "rha::AxiStreamDma::closeShared(");
    REQUIRE_MESSAGE(!openBody.empty(),
        "could not locate AxiStreamDma::openShared body for lock-guard verification");
    REQUIRE_MESSAGE(!closeBody.empty(),
        "could not locate AxiStreamDma::closeShared body for lock-guard verification");

    auto holdsLockOnMutex = [](const std::string& body) {
        const bool hasGuard =
            body.find("lock_guard<std::mutex>") != std::string::npos ||
            body.find("unique_lock<std::mutex>") != std::string::npos ||
            body.find("scoped_lock<std::mutex>") != std::string::npos ||
            body.find("std::lock_guard") != std::string::npos ||
            body.find("std::unique_lock") != std::string::npos ||
            body.find("std::scoped_lock") != std::string::npos;
        const bool referencesMutex =
            body.find("sharedBuffersMtx") != std::string::npos ||
            body.find("sharedMtx") != std::string::npos ||
            body.find("sharedBuffers_Mtx") != std::string::npos;
        return hasGuard && referencesMutex;
    };

    CHECK_MESSAGE(holdsLockOnMutex(openBody),
        " regression: AxiStreamDma::openShared() must take a "
        "std::lock_guard on the sharedBuffers_ mutex before touching the "
        "static map; without it concurrent construction can corrupt the map");
    CHECK_MESSAGE(holdsLockOnMutex(closeBody),
        " regression: AxiStreamDma::closeShared() must take a "
        "std::lock_guard on the sharedBuffers_ mutex before mutating the "
        "shared descriptor and the static map");
}
