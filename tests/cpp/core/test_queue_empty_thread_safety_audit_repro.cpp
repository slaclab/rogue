/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Queue::empty() reads queue_.empty() without holding mtx_.
 *
 * include/rogue/Queue.h::empty() (line 102) returns `queue_.empty()`
 * without taking `mtx_`. All other mutating operations (push, pop, reset)
 * take the lock. A concurrent push and empty() call can observe the queue
 * in an intermediate state, violating the expected linearisability contract.
 *
 * This test uses a source-text invariant (100% deterministic): reads
 * Queue.h and asserts that the `empty()` method body holds
 * std::unique_lock<std::mutex> before calling queue_.empty(). On HEAD the
 * method contains no lock → FAIL fires.
 *
 * A secondary structural assertion confirms `size()` DOES take the lock
 * (it is the fixed reference implementation), and that `empty()` does NOT
 * — reproducing the asymmetry that constitutes the bug.
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
#include <string>

#include "doctest/doctest.h"
#include "rogue/Queue.h"

namespace {

std::string readFile(const std::string& path) {
    std::ifstream f(path);
    if (!f.is_open()) return "";
    return std::string((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
}

/**
 * @brief Extract the substring of src that starts at the first occurrence of
 *        @p method_prefix and ends at the matching closing brace of the
 *        method body (brace-counting), so adjacent methods are not included.
 *
 * The function scans forward from method_prefix until it finds the opening
 * '{', then counts braces until depth returns to zero.  This prevents the
 * coarse max_chars approach from bleeding into a subsequent method's body.
 */
std::string extractMethodBody(const std::string& src, const std::string& method_prefix) {
    size_t pos = src.find(method_prefix);
    if (pos == std::string::npos) return "";

    // Advance to the opening brace of the method body.
    size_t brace_start = src.find('{', pos);
    if (brace_start == std::string::npos) return "";

    int depth = 0;
    size_t i   = brace_start;
    for (; i < src.size(); ++i) {
        if (src[i] == '{') {
            ++depth;
        } else if (src[i] == '}') {
            --depth;
            if (depth == 0) {
                // i is the closing brace of the method body.
                return src.substr(pos, i - pos + 1);
            }
        }
    }
    // Malformed source — return what we have.
    return src.substr(pos, i - pos);
}

}  // namespace

TEST_CASE("Queue::empty() acquires mutex before reading queue_") {
    // Read Queue.h and inspect the empty() method body.
    //
    // On HEAD:
    //   bool empty() {
    //       return queue_.empty();   // ← no lock taken
    //   }
    //
    // The fix:
    //   bool empty() {
    //       std::unique_lock<std::mutex> lock(mtx_);
    //       return queue_.empty();
    //   }
    //
    // Discriminator: the empty() body should contain "unique_lock" or
    // "lock_guard" just as size() already does.

    const std::string src = readFile(std::string(ROGUE_SRC_DIR) + "/include/rogue/Queue.h");

    REQUIRE_MESSAGE(!src.empty(),
                    "could not open include/rogue/Queue.h (ROGUE_SRC_DIR=",
                    ROGUE_SRC_DIR, ")");

    // Extract the empty() method body (up to ~200 chars starting at the decl).
    std::string empty_body = extractMethodBody(src, "bool empty()");
    REQUIRE_MESSAGE(!empty_body.empty(), "could not locate bool empty() in Queue.h");

    // Extract the size() method body for reference (it is correct).
    std::string size_body = extractMethodBody(src, "uint32_t size()");
    REQUIRE_MESSAGE(!size_body.empty(), "could not locate uint32_t size() in Queue.h");

    // Reference check: size() must use a lock (this is already true on HEAD).
    bool size_has_lock = (size_body.find("unique_lock") != std::string::npos ||
                          size_body.find("lock_guard")  != std::string::npos);
    CHECK_MESSAGE(size_has_lock,
                  "reference check failed — size() does not take mtx_; "
                  "the test assumption about the reference implementation is wrong.");

    // Primary assertion: empty() must also use a lock.
    bool empty_has_lock = (empty_body.find("unique_lock") != std::string::npos ||
                           empty_body.find("lock_guard")  != std::string::npos);

    CHECK_MESSAGE(empty_has_lock,
                  "Queue::empty() body lacks std::unique_lock<std::mutex>; "
                  "it reads queue_.empty() without holding mtx_ while push()/pop() "
                  "both take the lock. Concurrent push+empty() can observe an "
                  "inconsistent queue state (not thread-safe).");
}
