/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Logging::setFilter raw-pointer leak.
 *
 * src/rogue/Logging.cpp::setFilter (line 157) allocates a new LogFilter
 * with `new rogue::LogFilter(...)` and pushes the raw pointer onto the
 * static `filters_` vector. There is no corresponding `delete` in
 * `~Logging()`, `setFilter`, or any public API call. The filter list grows
 * without bound and the allocations are never freed.
 *
 * This test verifies the fix via a source-text invariant (100% deterministic):
 * reads Logging.cpp and asserts that ownership management (unique_ptr) exists
 * for the LogFilter pointers stored by setFilter.
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

TEST_CASE("Logging::setFilter does not leak LogFilter allocations — source invariant") {
    // Read the Logging.cpp source and verify that a delete/free/reset path
    // exists for the raw pointer pushed by setFilter.  On HEAD no such path
    // exists → test fails deterministically.
    std::ifstream f(std::string(ROGUE_SRC_DIR) + "/src/rogue/Logging.cpp");
    REQUIRE_MESSAGE(f.is_open(),
                    "could not open src/rogue/Logging.cpp (ROGUE_SRC_DIR=",
                    ROGUE_SRC_DIR, ")");

    std::string content((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());

    // The fix would add one of: delete flt; clearFilters(); std::unique_ptr
    // On HEAD none of these exist for the LogFilter pointer from setFilter.
    bool has_delete_flt   = content.find("delete flt")    != std::string::npos;
    bool has_clear        = content.find("clearFilters")  != std::string::npos;
    bool has_unique_ptr   = content.find("unique_ptr<rogue::LogFilter>") != std::string::npos
                         || content.find("unique_ptr<LogFilter>")        != std::string::npos;

    bool has_ownership_management = has_delete_flt || has_clear || has_unique_ptr;

    CHECK_MESSAGE(has_ownership_management,
                  "Logging::setFilter leaks LogFilter; "
                  "no delete/clearFilters/unique_ptr found in Logging.cpp. "
                  "Raw pointer pushed to static filters_ vector is never freed.");
}
