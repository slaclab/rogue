/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Compile-time guard that every worker-thread enable flag in the project
 * stays declared as ``std::atomic<bool>``. A plain ``bool`` allows the
 * compiler to hoist the read out of ``while (threadEn_) { ... }`` and is a
 * data race against the caller-thread store performed in ``stop()``. The
 * bug is invisible on most x86 builds (single-byte writes are naturally
 * atomic and the work loop's syscalls inhibit hoisting), so a behavioral
 * test cannot reliably catch the regression without ThreadSanitizer. A
 * compile-time check does, by failing the build the moment the type is
 * downgraded.
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
#include "rogue/hardware/MemMap.h"
#include "rogue/hardware/axi/AxiMemMap.h"
#include "rogue/hardware/axi/AxiStreamDma.h"
#include "rogue/interfaces/ZmqClient.h"
#include "rogue/interfaces/ZmqServer.h"
#include "rogue/interfaces/memory/TcpClient.h"
#include "rogue/interfaces/memory/TcpServer.h"
#include "rogue/interfaces/stream/Fifo.h"
#include "rogue/interfaces/stream/TcpCore.h"
#include "rogue/protocols/packetizer/Application.h"
#include "rogue/protocols/packetizer/Transport.h"
#include "rogue/protocols/rssi/Application.h"
#include "rogue/protocols/rssi/Controller.h"
#include "rogue/protocols/srp/SrpV3Emulation.h"
#include "rogue/protocols/udp/Core.h"
#include "rogue/protocols/xilinx/Xvc.h"
#include "rogue/utilities/Prbs.h"
#include "rogue/utilities/fileio/StreamReader.h"

namespace {

// Subclasses are needed because ``threadEn_`` is a protected member; a friend
// declaration would require touching the production headers, which defeats
// the point of an out-of-tree contract test.

#define ROGUE_THREADEN_PROBE(probe_name, qualified_class, base_alias)                          \
    struct probe_name : public qualified_class {                                               \
        using base_alias::base_alias;                                                          \
        static_assert(std::is_same<decltype(threadEn_), std::atomic<bool>>::value,             \
                      #qualified_class "::threadEn_ must be std::atomic<bool>");               \
    }

ROGUE_THREADEN_PROBE(TcpCoreFlagProbe, rogue::interfaces::stream::TcpCore, TcpCore);
ROGUE_THREADEN_PROBE(UdpCoreFlagProbe, rogue::protocols::udp::Core, Core);
ROGUE_THREADEN_PROBE(AxiStreamDmaFlagProbe, rogue::hardware::axi::AxiStreamDma, AxiStreamDma);
ROGUE_THREADEN_PROBE(MemMapFlagProbe, rogue::hardware::MemMap, MemMap);
ROGUE_THREADEN_PROBE(AxiMemMapFlagProbe, rogue::hardware::axi::AxiMemMap, AxiMemMap);
ROGUE_THREADEN_PROBE(ZmqClientFlagProbe, rogue::interfaces::ZmqClient, ZmqClient);
ROGUE_THREADEN_PROBE(ZmqServerFlagProbe, rogue::interfaces::ZmqServer, ZmqServer);
ROGUE_THREADEN_PROBE(MemoryTcpClientFlagProbe, rogue::interfaces::memory::TcpClient, TcpClient);
ROGUE_THREADEN_PROBE(MemoryTcpServerFlagProbe, rogue::interfaces::memory::TcpServer, TcpServer);
ROGUE_THREADEN_PROBE(PacketizerApplicationFlagProbe, rogue::protocols::packetizer::Application, Application);
ROGUE_THREADEN_PROBE(PacketizerTransportFlagProbe, rogue::protocols::packetizer::Transport, Transport);
ROGUE_THREADEN_PROBE(RssiApplicationFlagProbe, rogue::protocols::rssi::Application, Application);
ROGUE_THREADEN_PROBE(SrpV3EmulationFlagProbe, rogue::protocols::srp::SrpV3Emulation, SrpV3Emulation);
ROGUE_THREADEN_PROBE(PrbsFlagProbe, rogue::utilities::Prbs, Prbs);
ROGUE_THREADEN_PROBE(StreamReaderFlagProbe, rogue::utilities::fileio::StreamReader, StreamReader);
ROGUE_THREADEN_PROBE(FifoFlagProbe, rogue::interfaces::stream::Fifo, Fifo);
ROGUE_THREADEN_PROBE(RssiControllerFlagProbe, rogue::protocols::rssi::Controller, Controller);
ROGUE_THREADEN_PROBE(XvcFlagProbe, rogue::protocols::xilinx::Xvc, Xvc);

#undef ROGUE_THREADEN_PROBE

}  // namespace

TEST_CASE("worker-thread enable flags are std::atomic<bool>") {
    // The real assertions are at compile time; this body just keeps the
    // probe types from being eliminated as unused and produces a runtime
    // pass for the test harness.
    CHECK(sizeof(TcpCoreFlagProbe) >= sizeof(std::atomic<bool>));
    CHECK(sizeof(UdpCoreFlagProbe) >= sizeof(std::atomic<bool>));
    CHECK(sizeof(AxiStreamDmaFlagProbe) >= sizeof(std::atomic<bool>));
    CHECK(sizeof(MemMapFlagProbe) >= sizeof(std::atomic<bool>));
    CHECK(sizeof(AxiMemMapFlagProbe) >= sizeof(std::atomic<bool>));
    CHECK(sizeof(ZmqClientFlagProbe) >= sizeof(std::atomic<bool>));
    CHECK(sizeof(ZmqServerFlagProbe) >= sizeof(std::atomic<bool>));
    CHECK(sizeof(MemoryTcpClientFlagProbe) >= sizeof(std::atomic<bool>));
    CHECK(sizeof(MemoryTcpServerFlagProbe) >= sizeof(std::atomic<bool>));
    CHECK(sizeof(PacketizerApplicationFlagProbe) >= sizeof(std::atomic<bool>));
    CHECK(sizeof(PacketizerTransportFlagProbe) >= sizeof(std::atomic<bool>));
    CHECK(sizeof(RssiApplicationFlagProbe) >= sizeof(std::atomic<bool>));
    CHECK(sizeof(SrpV3EmulationFlagProbe) >= sizeof(std::atomic<bool>));
    CHECK(sizeof(PrbsFlagProbe) >= sizeof(std::atomic<bool>));
    CHECK(sizeof(StreamReaderFlagProbe) >= sizeof(std::atomic<bool>));
    CHECK(sizeof(FifoFlagProbe) >= sizeof(std::atomic<bool>));
    CHECK(sizeof(RssiControllerFlagProbe) >= sizeof(std::atomic<bool>));
    CHECK(sizeof(XvcFlagProbe) >= sizeof(std::atomic<bool>));
}
