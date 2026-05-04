/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Audit repro for UTIL-005: StreamReader::close() acquires mtx_ before
 * calling intClose() -> readThread_->join().  The reader thread's exit path
 * (runThread end, line 241) also acquires mtx_ before clearing active_ and
 * notifying cond_.  This causes a deadlock any time close() is called while
 * the reader thread is finishing: the calling thread holds mtx_ while waiting
 * in join(), and the worker waits to acquire mtx_.
 *
 * Deterministic source-text invariant: reads StreamReader.cpp and asserts
 * that close() does NOT acquire mtx_ before calling intClose()/join().
 * On HEAD close() does acquire mtx_ first -> CHECK_MESSAGE fires.
 *
 * Note: no std::this_thread::sleep_for + unconditional assert is used
 * (per the plan's no-timing constraint).
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
#include <vector>

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

// Split source text into lines for window analysis
static std::vector<std::string> splitLines(const std::string& src) {
    std::vector<std::string> lines;
    std::istringstream ss(src);
    std::string line;
    while (std::getline(ss, line)) lines.push_back(line);
    return lines;
}

TEST_CASE("UTIL-005: StreamReader::close() deadlock -- holds mtx_ during join()") {
    const std::string src = readFile(
        ROGUE_SRC_DIR "/src/rogue/utilities/fileio/StreamReader.cpp");
    REQUIRE_MESSAGE(!src.empty(), "Could not read fileio/StreamReader.cpp");

    // Locate the close() function body.  The function starts with:
    //   "void ruf::StreamReader::close() {"
    const std::string closeSig = "StreamReader::close()";
    const std::size_t closePos = src.find(closeSig);
    REQUIRE_MESSAGE(closePos != std::string::npos,
                    "Could not locate StreamReader::close() in StreamReader.cpp");

    // Extract the close() body (300 bytes covers the entire short function)
    const std::string closeBody = src.substr(closePos, 300);

    // Locate the runThread exit path (at line ~241).  The worker acquires
    // mtx_ here: "std::unique_lock<std::mutex> lock(mtx_);"
    const std::string runThreadSig = "StreamReader::runThread";
    const std::size_t runThreadPos = src.find(runThreadSig);
    REQUIRE_MESSAGE(runThreadPos != std::string::npos,
                    "Could not locate StreamReader::runThread");

    // Extract tail of runThread (last 300 bytes before end of function)
    const std::string runThreadEnd = src.substr(
        (runThreadPos + 100 > src.size()) ? 0 : runThreadPos + 100, 2000);

    // Deadlock condition: close() holds mtx_ before join() AND runThread()
    // acquires mtx_ at its exit point.
    const bool closeHoldsMtx = (closeBody.find("lock(mtx_)") != std::string::npos ||
                                 closeBody.find("mtx_.lock()") != std::string::npos);
    const bool runThreadAcquiresMtx =
        (runThreadEnd.find("lock(mtx_)") != std::string::npos ||
         runThreadEnd.find("mtx_.lock()") != std::string::npos);

    // Both must be false for the fix to be in place.
    // On HEAD: closeHoldsMtx=true, runThreadAcquiresMtx=true -> deadlock.
    CHECK_MESSAGE(!closeHoldsMtx,
                  "UTIL-005: StreamReader::close() acquires mtx_ before "
                  "calling intClose()/join(); runThread() also acquires mtx_ "
                  "at its exit -- structural deadlock: caller holds mtx_ while "
                  "waiting in join(), worker waits for mtx_");
}
