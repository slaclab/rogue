/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Logging ctor/dtor use raw lock()/unlock() rather than RAII locking.
 *
 *  (src/rogue/Logging.cpp:109): Logging::Logging() calls
 *   levelMtx_.lock();... levelMtx_.unlock();
 * instead of using std::lock_guard<std::mutex>.  If any code between lock
 * and unlock throws (e.g. loggers_.push_back can throw std::bad_alloc),
 * the mutex is held forever → all subsequent log operations deadlock.
 *
 *  (src/rogue/Logging.cpp:121): Logging::~Logging() had the same
 * raw lock/unlock pattern. Using std::lock_guard is preferred for consistency
 * and to follow RAII conventions even when the operations are non-throwing.
 *
 * Both tests use source-text inspection to assert that RAII locking
 * (lock_guard, unique_lock, or scoped_lock) is used instead of raw
 * lock/unlock. On HEAD raw lock/unlock is present → FAIL.
 *
 * The ROGUE_SRC_DIR macro is injected by the CMakeLists via
 * target_compile_definitions so the source path resolves at test runtime.
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
#include "rogue/Logging.h"

namespace {

/**
 * @brief Read the entire contents of a file into a std::string.
 * @return File contents, or empty string if file could not be opened.
 */
std::string readFile(const std::string& path) {
    std::ifstream f(path);
    if (!f.is_open()) return "";
    return std::string((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
}

}  // namespace

TEST_CASE("Logging constructor uses std::lock_guard instead of raw lock/unlock") {
    // Read Logging.cpp and verify the constructor body uses std::lock_guard
    // (or std::unique_lock / std::scoped_lock) rather than raw levelMtx_.lock().
    const std::string src = readFile(std::string(ROGUE_SRC_DIR) + "/src/rogue/Logging.cpp");

    REQUIRE_MESSAGE(!src.empty(),
                    "could not open src/rogue/Logging.cpp (ROGUE_SRC_DIR=",
                    ROGUE_SRC_DIR, ")");

    // On HEAD: levelMtx_.lock() / levelMtx_.unlock() are present in the ctor body.
    bool has_raw_lock   = src.find("levelMtx_.lock()")   != std::string::npos;
    bool has_lock_guard = src.find("std::lock_guard")     != std::string::npos
                       || src.find("std::unique_lock")    != std::string::npos
                       || src.find("std::scoped_lock")    != std::string::npos;

    // A properly fixed implementation uses lock_guard and no raw lock/unlock.
    CHECK_MESSAGE(!has_raw_lock,
                  "Logging::Logging() uses raw levelMtx_.lock(); "
                  "if loggers_.push_back() throws, the mutex is held forever. "
                  "Replace with std::lock_guard<std::mutex>.");

    CHECK_MESSAGE(has_lock_guard,
                  "Logging.cpp does not use std::lock_guard / "
                  "std::unique_lock / std::scoped_lock; fix must introduce RAII locking.");
}

TEST_CASE("Logging destructor uses std::lock_guard instead of raw lock/unlock") {
    // Read Logging.cpp and verify the destructor body uses RAII locking.
    // On HEAD the destructor at line 121 calls levelMtx_.lock() / unlock()
    // directly; std::lock_guard is preferred for RAII consistency.
    const std::string src = readFile(std::string(ROGUE_SRC_DIR) + "/src/rogue/Logging.cpp");

    REQUIRE_MESSAGE(!src.empty(),
                    "could not open src/rogue/Logging.cpp (ROGUE_SRC_DIR=",
                    ROGUE_SRC_DIR, ")");

    // The simplest discriminator: after the fix, raw levelMtx_.lock() should
    // not appear at all (both ctor and dtor are fixed together).
    bool has_raw_lock = src.find("levelMtx_.lock()") != std::string::npos;

    CHECK_MESSAGE(!has_raw_lock,
                  "Logging::~Logging() uses raw levelMtx_.lock(); "
                  "replace with std::lock_guard<std::mutex> for RAII consistency.");
}
