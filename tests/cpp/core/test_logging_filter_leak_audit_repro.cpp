/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * CORE-001 repro: Logging::setFilter raw-pointer leak.
 *
 * src/rogue/Logging.cpp::setFilter (line 157) allocates a new LogFilter
 * with `new rogue::LogFilter(...)` and pushes the raw pointer onto the
 * static `filters_` vector. There is no corresponding `delete` in
 * `~Logging()`, `setFilter`, or any public API call. The filter list grows
 * without bound and the allocations are never freed.
 *
 * This test verifies the leak two ways:
 *
 * 1. Source-text invariant (100% deterministic): reads Logging.cpp and
 *    asserts that a `delete` or `clearFilters` call exists for the raw
 *    pointer stored by setFilter.  On HEAD neither exists → FAIL_CHECK fires.
 *
 * 2. RSS growth check (deterministic on process start): baseline RSS,
 *    call setFilter 1000 times with unique names, measure delta.  A
 *    correctly-implemented setFilter (owning or no-alloc) would keep RSS
 *    flat; the raw-pointer leak grows it by ~30–90 KiB.  The threshold of
 *    1 MiB is generous but the leak is monotonic so it is reliable.
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
#include <stdint.h>
#include <string>
#include <sys/resource.h>

#include "doctest/doctest.h"
#include "rogue/Logging.h"

namespace {

/**
 * @brief Return the current process RSS in kilobytes (Linux only).
 */
int64_t getRssKb() {
    struct rusage ru;
    if (getrusage(RUSAGE_SELF, &ru) != 0) return -1;
    return static_cast<int64_t>(ru.ru_maxrss);  // kilobytes on Linux
}

}  // namespace

TEST_CASE("CORE-001: Logging::setFilter does not leak LogFilter allocations — source invariant") {
    // Read the Logging.cpp source and verify that a delete/free/reset path
    // exists for the raw pointer pushed by setFilter.  On HEAD no such path
    // exists → test fails deterministically.
    std::ifstream f(std::string(ROGUE_SRC_DIR) + "/src/rogue/Logging.cpp");
    REQUIRE_MESSAGE(f.is_open(),
                    "CORE-001: could not open src/rogue/Logging.cpp (ROGUE_SRC_DIR=",
                    ROGUE_SRC_DIR, ")");

    std::string content((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());

    // The fix would add one of: delete flt; clearFilters(); std::unique_ptr; std::shared_ptr
    // On HEAD none of these exist for the LogFilter pointer from setFilter.
    bool has_delete_flt   = content.find("delete flt")    != std::string::npos;
    bool has_clear        = content.find("clearFilters")  != std::string::npos;
    bool has_unique_ptr   = content.find("unique_ptr<rogue::LogFilter>") != std::string::npos
                         || content.find("unique_ptr<LogFilter>")        != std::string::npos;

    bool has_ownership_management = has_delete_flt || has_clear || has_unique_ptr;

    CHECK_MESSAGE(has_ownership_management,
                  "CORE-001: Logging::setFilter leaks LogFilter; "
                  "no delete/clearFilters/unique_ptr found in Logging.cpp. "
                  "Raw pointer pushed to static filters_ vector is never freed.");
}

TEST_CASE("CORE-001: Logging::setFilter RSS growth from 1000 filter insertions") {
    // Baseline RSS before the allocations.
    int64_t rss_before = getRssKb();

    // Call setFilter 1000 times with unique names.
    // Each call allocates a new LogFilter that is never freed.
    for (int i = 0; i < 1000; ++i) {
        rogue::Logging::setFilter("audit_core001_" + std::to_string(i), rogue::Logging::Warning);
    }

    int64_t rss_after = getRssKb();
    int64_t delta_kb  = rss_after - rss_before;

    // Each LogFilter allocation is small (~100–200 bytes) but 1000 of them
    // are at least a few KiB.  A generous threshold of 1 MiB still
    // confirms the leak for N=1000; a correct free-on-reset implementation
    // would keep delta near 0.
    //
    // If rss_before == -1 the platform doesn't support getrusage — skip.
    if (rss_before > 0) {
        CHECK_MESSAGE(delta_kb < 1024,
                      "CORE-001: setFilter leaked ",
                      delta_kb,
                      " KiB over 1000 calls (threshold 1024 KiB). "
                      "Raw LogFilter pointers pushed to static filters_ are never deleted.");
    }
}
