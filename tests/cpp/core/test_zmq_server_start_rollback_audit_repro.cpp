/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression test for ZmqServer::start exception-safety.
 *
 * On HEAD before the fix, ZmqServer::start() set threadEn_ = true and then
 * constructed rThread_ and sThread_ without any try/catch.  If either
 * std::make_unique<std::thread>(...) call threw (std::system_error from the
 * worker constructor or std::bad_alloc from the unique_ptr allocation), the
 * server was left with threadEn_ == true but at most one running worker.
 * A subsequent start() would short-circuit at the `if (threadEn_) return;`
 * guard, so the server was permanently stuck half-started.
 *
 * Source-text invariant test: confirm ZmqServer::start contains a try / catch
 * around the thread constructions, with the catch path resetting threadEn_
 * and joining whichever thread did succeed before re-throwing.
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
#include "rogue/Directives.h"

#include <fstream>
#include <sstream>
#include <string>

#include "doctest/doctest.h"

#ifndef ROGUE_SRC_DIR
    #error "ROGUE_SRC_DIR must be defined via target_compile_definitions"
#endif

namespace {

std::string readFile(const std::string& path) {
    std::ifstream f(path);
    if (!f.is_open()) return "";
    std::ostringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

// Extract the body of a member function definition.  Returns the substring
// from the opening '{' of the matching definition to the matching '}'.
std::string extractFunctionBody(const std::string& src, const std::string& signaturePrefix) {
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

}  // namespace

TEST_CASE("ZmqServer::start rolls back threadEn_ when thread construction throws") {
    const std::string src =
        readFile(std::string(ROGUE_SRC_DIR) + "/src/rogue/interfaces/ZmqServer.cpp");
    REQUIRE_MESSAGE(!src.empty(), "could not open src/rogue/interfaces/ZmqServer.cpp");

    const std::string body = extractFunctionBody(src, "rogue::interfaces::ZmqServer::start(");
    REQUIRE_MESSAGE(!body.empty(), "could not locate ZmqServer::start body");

    // The fix must locate the threadEn_ = true assignment and the rThread_/sThread_
    // constructions inside a try block, and the matching catch must reset
    // threadEn_ to false before re-throwing so a subsequent start() can re-arm.
    const bool hasTry        = body.find("try ") != std::string::npos
                            || body.find("try{") != std::string::npos;
    const bool hasCatch      = body.find("catch") != std::string::npos;
    const bool resetsFlag    = body.find("threadEn_ = false") != std::string::npos;
    const bool reThrows      = body.find("throw;") != std::string::npos;
    const bool joinsRThread  = body.find("rThread_->join()") != std::string::npos;
    const bool joinsSThread  = body.find("sThread_->join()") != std::string::npos;

    CHECK_MESSAGE(hasTry,
        "ZmqServer::start must wrap the rThread_/sThread_ construction in a try block; "
        "without rollback, an exception from std::make_unique<std::thread>(...) leaves "
        "threadEn_ == true with no workers and a later start() returns early.");
    CHECK_MESSAGE(hasCatch,
        "ZmqServer::start must catch the rethrown exception so it can roll back "
        "threadEn_ and join whichever thread did get constructed.");
    CHECK_MESSAGE(resetsFlag,
        "ZmqServer::start catch block must reset threadEn_ = false; otherwise the "
        "object is stuck half-started and re-entering start() short-circuits.");
    CHECK_MESSAGE(reThrows,
        "ZmqServer::start catch block must re-throw the original exception so the "
        "caller still sees the failure; silently swallowing it would mask configuration bugs.");
    CHECK_MESSAGE(joinsRThread,
        "ZmqServer::start catch block must join rThread_ if it was successfully started "
        "before propagating, otherwise the worker keeps running with the object torn down.");
    CHECK_MESSAGE(joinsSThread,
        "ZmqServer::start catch block must join sThread_ if it was successfully started "
        "before propagating; symmetry with rThread_.");
}
