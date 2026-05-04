/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * CORE-005 repro: Version::init() mutates static members without a mutex.
 *
 * src/rogue/Version.cpp::init() (line 43) writes to the static members
 * `_major`, `_minor`, `_maint`, `_devel` without holding any mutex.
 * Every comparison helper (greaterThanEqual, greaterThan, lessThanEqual,
 * lessThan, getMajor, getMinor, getMaint, getDevel, pythonVersion) calls
 * init() before reading these statics. Two concurrent callers can race,
 * producing torn reads or torn writes on platforms where multi-word stores
 * are not atomic.
 *
 * Because the race is undefined behaviour and requires Thread Sanitizer or
 * precise ordering to detect at runtime, this test uses a 100% deterministic
 * source-text invariant: reads Version.cpp and asserts that `_major` is
 * declared std::atomic<uint32_t> or that init() is guarded by
 * std::call_once / a mutex. On HEAD neither exists → FAIL fires.
 *
 * A secondary structural check: greaterThanEqual() calls init() every time
 * it is invoked (even after the values are already populated). Assert that
 * the source contains a std::call_once / once_flag guard or similar
 * idempotency protection; on HEAD it does not.
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
#include "rogue/Version.h"

namespace {

std::string readFile(const std::string& path) {
    std::ifstream f(path);
    if (!f.is_open()) return "";
    return std::string((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
}

}  // namespace

TEST_CASE("CORE-005: Version::init() protects static member writes from concurrent access") {
    // Read Version.cpp and Version.h and verify that the static _major/_minor/_maint/_devel
    // are declared std::atomic or that init() is called at most once via std::call_once.
    //
    // On HEAD:
    //   - Version.cpp declares `uint32_t rogue::Version::_major = 0;` (plain uint32_t)
    //   - init() unconditionally re-assigns _major/_minor/_maint/_devel
    //   - No std::call_once or mutex is used in init()
    // → FAIL_CHECK fires deterministically.

    const std::string src_cpp =
        readFile(std::string(ROGUE_SRC_DIR) + "/src/rogue/Version.cpp");
    const std::string src_h =
        readFile(std::string(ROGUE_SRC_DIR) + "/include/rogue/Version.h");

    REQUIRE_MESSAGE(!src_cpp.empty(),
                    "CORE-005: could not open src/rogue/Version.cpp (ROGUE_SRC_DIR=",
                    ROGUE_SRC_DIR, ")");
    REQUIRE_MESSAGE(!src_h.empty(),
                    "CORE-005: could not open include/rogue/Version.h (ROGUE_SRC_DIR=",
                    ROGUE_SRC_DIR, ")");

    // Check 1: _major should be declared as std::atomic<uint32_t> in the header
    // or as a private static std::atomic member.
    bool major_is_atomic = (src_h.find("atomic<uint32_t>") != std::string::npos &&
                            src_h.find("_major")           != std::string::npos)
                        || (src_h.find("std::atomic")      != std::string::npos &&
                            src_h.find("_major")           != std::string::npos);

    CHECK_MESSAGE(major_is_atomic,
                  "CORE-005: Version::_major is not declared std::atomic<uint32_t>; "
                  "concurrent calls to init() introduce a data race on _major/_minor/_maint/_devel. "
                  "Declare the statics as std::atomic<uint32_t> or guard init() with std::call_once.");

    // Check 2: init() should be idempotent — guarded by std::call_once or an initialised-flag check.
    bool has_call_once  = src_cpp.find("call_once")   != std::string::npos;
    bool has_once_flag  = src_cpp.find("once_flag")   != std::string::npos;
    bool has_init_guard = has_call_once || has_once_flag;

    CHECK_MESSAGE(has_init_guard,
                  "CORE-005: Version::init() does not use std::call_once / std::once_flag; "
                  "it unconditionally rewrites _major/_minor/_maint/_devel on every call, "
                  "making every comparison helper subject to a data race. "
                  "Add `static std::once_flag flag; std::call_once(flag, [](){ ... });`.");
}
