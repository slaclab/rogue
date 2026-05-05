/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression test for stream::TcpCore::stop() racing with concurrent
 * acceptFrame() / rebuildPushSocket() calls.
 *
 * Background:
 *   acceptFrame() and rebuildPushSocket() take bridgeMtx_ to serialise
 *   their access to zmqPush_/zmqCtx_, but stop() previously closed the
 *   sockets and destroyed the context without taking the same lock.  A
 *   Python _stop call from one thread could therefore race a frame send
 *   on another thread and free ZMQ handles while they were in use,
 *   risking crashes or undefined behaviour.
 *
 * Source-text invariants (matching the established audit-repro pattern):
 *
 *   1. stop() acquires bridgeMtx_ before its zmq_close calls.
 *   2. acceptFrame() bails out when threadEn_ is false (the post-stop
 *      state) so any caller that takes the mutex after teardown sees the
 *      bridge as stopped instead of dereferencing freed handles.
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
#include <stdint.h>

#include <fstream>
#include <sstream>
#include <string>

#include "doctest/doctest.h"

#ifndef ROGUE_SRC_DIR
    #define ROGUE_SRC_DIR "."
#endif

static std::string readFile(const std::string& path) {
    std::ifstream f(path);
    if (!f.is_open()) return std::string();
    std::ostringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

TEST_CASE("stream::TcpCore::stop serialises socket teardown with bridgeMtx_") {
    const std::string src = readFile(
        ROGUE_SRC_DIR "/src/rogue/interfaces/stream/TcpCore.cpp");
    REQUIRE_MESSAGE(!src.empty(), "Could not read stream/TcpCore.cpp");

    // Locate the stop() function definition.
    const std::size_t fnStart = src.find("ris::TcpCore::stop()");
    REQUIRE_MESSAGE(fnStart != std::string::npos,
                    "TcpCore::stop() definition not found");

    // Locate the first zmq_close call after the function start.
    const std::size_t closePos = src.find("zmq_close(", fnStart);
    REQUIRE_MESSAGE(closePos != std::string::npos,
                    "zmq_close call not found in stop()");

    const std::string region = src.substr(fnStart, closePos - fnStart);

    const bool hasMutexGuard = (
        region.find("lock_guard<std::mutex>(bridgeMtx_)") != std::string::npos ||
        region.find("lock_guard<std::mutex> lock(bridgeMtx_)") != std::string::npos ||
        region.find("unique_lock<std::mutex> lock(bridgeMtx_)") != std::string::npos ||
        region.find("bridgeMtx_.lock()") != std::string::npos);

    CHECK_MESSAGE(hasMutexGuard,
                  "TcpCore::stop() does not acquire bridgeMtx_ before "
                  "tearing down zmqPull_/zmqPush_/zmqCtx_; this races "
                  "with concurrent acceptFrame()/rebuildPushSocket() "
                  "callers and can free ZMQ handles while they are in use.");
}

TEST_CASE("stream::TcpCore::acceptFrame bails out when threadEn_ is false") {
    const std::string src = readFile(
        ROGUE_SRC_DIR "/src/rogue/interfaces/stream/TcpCore.cpp");
    REQUIRE_MESSAGE(!src.empty(), "Could not read stream/TcpCore.cpp");

    // Locate the acceptFrame() function definition.
    const std::size_t fnStart = src.find("ris::TcpCore::acceptFrame(");
    REQUIRE_MESSAGE(fnStart != std::string::npos,
                    "TcpCore::acceptFrame() definition not found");

    // Locate the first zmq_sendmsg call after the function start.
    const std::size_t sendPos = src.find("zmq_sendmsg(this->zmqPush_", fnStart);
    REQUIRE_MESSAGE(sendPos != std::string::npos,
                    "zmq_sendmsg(this->zmqPush_, ...) call not found in acceptFrame()");

    const std::string region = src.substr(fnStart, sendPos - fnStart);

    const bool hasStoppedGuard = (
        region.find("!threadEn_") != std::string::npos ||
        region.find("threadEn_ == false") != std::string::npos ||
        region.find("!this->threadEn_") != std::string::npos);

    CHECK_MESSAGE(hasStoppedGuard,
                  "TcpCore::acceptFrame() does not bail out when "
                  "threadEn_ is false; once stop() has torn down the "
                  "sockets/context, a late acceptFrame() that takes "
                  "bridgeMtx_ would otherwise dereference freed ZMQ "
                  "handles.");
}
