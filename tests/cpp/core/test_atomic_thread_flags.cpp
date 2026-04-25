/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Compile-time guard that the worker-thread enable flag in TcpCore, the UDP
 * Core, and AxiStreamDma stays declared as ``std::atomic<bool>``. A plain
 * ``bool`` allows the compiler to hoist the read out of
 * ``while (threadEn_) { ... }`` and is a data race against the caller-thread
 * store performed in ``stop()``. The bug is invisible on most x86 builds
 * (single-byte writes are naturally atomic and the work loop's syscalls
 * inhibit hoisting), so a behavioral test cannot reliably catch the
 * regression without ThreadSanitizer. A compile-time check does, by failing
 * the build the moment the type is downgraded.
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
#include <atomic>
#include <type_traits>

#include "doctest/doctest.h"
#include "rogue/hardware/axi/AxiStreamDma.h"
#include "rogue/interfaces/stream/TcpCore.h"
#include "rogue/protocols/udp/Core.h"

namespace {

// Subclasses are needed because ``threadEn_`` is a protected member; a friend
// declaration would require touching the production headers, which defeats
// the point of an out-of-tree contract test.

struct TcpCoreFlagProbe : public rogue::interfaces::stream::TcpCore {
    using TcpCore::TcpCore;
    static_assert(std::is_same<decltype(threadEn_), std::atomic<bool>>::value,
                  "rogue::interfaces::stream::TcpCore::threadEn_ must be std::atomic<bool>");
};

struct UdpCoreFlagProbe : public rogue::protocols::udp::Core {
    using Core::Core;
    static_assert(std::is_same<decltype(threadEn_), std::atomic<bool>>::value,
                  "rogue::protocols::udp::Core::threadEn_ must be std::atomic<bool>");
};

struct AxiStreamDmaFlagProbe : public rogue::hardware::axi::AxiStreamDma {
    using AxiStreamDma::AxiStreamDma;
    static_assert(std::is_same<decltype(threadEn_), std::atomic<bool>>::value,
                  "rogue::hardware::axi::AxiStreamDma::threadEn_ must be std::atomic<bool>");
};

}  // namespace

TEST_CASE("worker-thread enable flags are std::atomic<bool>") {
    // The real assertions are at compile time; this body just keeps the
    // probe types from being eliminated as unused and produces a runtime
    // pass for the test harness.
    CHECK(sizeof(TcpCoreFlagProbe) >= sizeof(std::atomic<bool>));
    CHECK(sizeof(UdpCoreFlagProbe) >= sizeof(std::atomic<bool>));
    CHECK(sizeof(AxiStreamDmaFlagProbe) >= sizeof(std::atomic<bool>));
}
