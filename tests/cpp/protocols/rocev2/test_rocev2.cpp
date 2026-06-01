/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Native C++ doctest coverage for the RoCEv2 Core and Server constructor paths.
 * Covers:
 *   - Graceful-error paths when the requested ibverbs device is not registered.
 *   - Hardware-gated happy-path tests that run only when a Soft-RoCE device
 *     named "rxe0" is present.  On hosts without rxe0 these TEST_CASEs
 *     early-return (equivalent to skipping — vendored doctest 2.4.12 has no
 *     DOCTEST_SKIP_CURRENT_TEST macro, so the `if (!rxeAvailable()) return;`
 *     idiom is the sanctioned fallback).
 * The Core / Server objects under test perform their own RAII via their
 * destructors, so no separate ibverbs RAII wrappers are needed.
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

#include <infiniband/verbs.h>

#include <string>

#include "doctest/doctest.h"

#include "rogue/GeneralError.h"
#include "rogue/protocols/rocev2/Core.h"
#include "rogue/protocols/rocev2/Server.h"

namespace {

// Deliberately-nonexistent ibverbs device name so the test behaves
// identically on CI (no devices at all) and on dev hosts (devices exist
// but none match this name).
constexpr const char* kMissingDevice = "__rogue_rocev2_nonexistent__";

// Constant device name used by the hardware-gated TEST_CASEs.  Matches the
// `rdma link add rxe0 type rxe netdev <iface>` bring-up invocation.
constexpr const char* kDev = "rxe0";

// Runtime probe: true iff an ibverbs device named "rxe0" is registered with
// the kernel.  Used by the `if (!rxeAvailable()) return;` skip idiom
// (vendored doctest 2.4.12 has no DOCTEST_SKIP_CURRENT_TEST macro).
bool rxeAvailable() {
    int num           = 0;
    ibv_device** list = ibv_get_device_list(&num);
    if (!list) return false;
    bool found = false;
    for (int i = 0; i < num; ++i) {
        if (std::string(kDev) == ibv_get_device_name(list[i])) {
            found = true;
            break;
        }
    }
    ibv_free_device_list(list);
    return found;
}

}  // namespace

TEST_CASE("rocev2 Core and Server throw GeneralError for missing devices") {
    SUBCASE("Core::Core with nonexistent device name") {
        CHECK_THROWS_AS(rogue::protocols::rocev2::Core(kMissingDevice, 1, 0), rogue::GeneralError);

        // Assert the graceful-error message carries one of the two expected
        // forms from src/rogue/protocols/rocev2/Core.cpp lines 63-79.
        try {
            rogue::protocols::rocev2::Core c(kMissingDevice, 1, 0);
            FAIL("Core::Core returned without throwing");
        } catch (const rogue::GeneralError& e) {
            const std::string msg(e.what());
            const bool noDevs   = msg.find("No RDMA devices found") != std::string::npos;
            const bool notFound = msg.find("not found") != std::string::npos;
            CHECK((noDevs || notFound));
        }
    }

    SUBCASE("Core::Core with empty device name") {
        CHECK_THROWS_AS(rogue::protocols::rocev2::Core("", 1, 0), rogue::GeneralError);
    }

    SUBCASE("Server::create with nonexistent device name") {
        CHECK_THROWS_AS(rogue::protocols::rocev2::Server::create(kMissingDevice, 1, 0), rogue::GeneralError);

        try {
            auto s = rogue::protocols::rocev2::Server::create(kMissingDevice, 1, 0);
            FAIL("Server::create returned without throwing");
        } catch (const rogue::GeneralError& e) {
            const std::string msg(e.what());
            const bool noDevs   = msg.find("No RDMA devices found") != std::string::npos;
            const bool notFound = msg.find("not found") != std::string::npos;
            CHECK((noDevs || notFound));
        }
    }
}

TEST_CASE("rocev2 Core opens rxe0 on a live device") {
    if (!rxeAvailable()) return;  // runtime-skip idiom (doctest 2.4.12 has no DOCTEST_SKIP_CURRENT_TEST)

    // Core owns the ibv_context and ibv_pd.  RAII check by scope:
    // ~Core at the closing brace releases both.  CQ / QP / MR live in the
    // derived Server class and are not constructed here.
    rogue::protocols::rocev2::Core c(kDev, 1, 0);
    CHECK(c.maxPayload() == rogue::protocols::rocev2::DefaultMaxPayload);
}

TEST_CASE("rocev2 Core and Server handle out-of-range gidIndex") {
    if (!rxeAvailable()) return;

    // Intended behavior:
    //   * Core::Core does NOT query the GID (Core has no GID field); Core
    //     accepts any gidIndex, including 255, without throwing.
    //   * Server::create DOES query the GID via ibv_query_gid inside
    //     the Server ctor; out-of-range gidIndex causes ibv_query_gid
    //     to return non-zero and the ctor to throw rogue::GeneralError.

    SUBCASE("Core accepts gidIndex=255 (no GID query)") {
        CHECK_NOTHROW(rogue::protocols::rocev2::Core(kDev, 1, 255));
    }

    SUBCASE("Server::create throws on gidIndex=255") {
        CHECK_THROWS_AS(rogue::protocols::rocev2::Server::create(kDev, 1, 255), rogue::GeneralError);
    }
}

TEST_CASE("rocev2 Server::create on a live rxe0 returns a valid ServerPtr") {
    if (!rxeAvailable()) return;

    auto s = rogue::protocols::rocev2::Server::create(kDev, 1, 0);
    REQUIRE(s != nullptr);
    CHECK_NE(s->getQpn(), 0u);
    CHECK_NE(s->getMrAddr(), 0u);
    CHECK_NE(s->getMrRkey(), 0u);
    CHECK(!s->getGid().empty());
    // shared_ptr destructor runs at scope end; ~Server calls stop() which
    // destroys QP/CQ/MR/slab. No explicit s->stop() needed (and calling
    // stop twice is safe per the idempotent guard in Server::stop).
}
