/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression test for the AxiStreamDma zero-copy teardown lifetime fix.
 *
 * A zero-copy Rogue Buffer points directly into the shared DMA mapping
 * (desc_->rawBuff, established by dmaMapDma()). Releasing that mapping inside
 * stop() left any frame retained past stop() pointing at unmapped memory. The
 * fix moves the shared-descriptor teardown out of stop() and into
 * ~AxiStreamDma(), so the mapping outlives stop() and is freed only at
 * destruction.
 *
 * The aes-stream-driver character device does not exist on CI runners, so this
 * test runs against the fake_dma_preload LD_PRELOAD shim (wired in by the
 * accompanying CMakeLists.txt). The shim reports how many DMA buffers are
 * currently mapped via fakedma_mapped_count(); the test asserts the mapping is
 * still present after stop() and released exactly at destruction. Reverting the
 * fix (moving closeShared() back into stop()) drops the count to zero at stop()
 * and fails the post-stop() check.
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
#include <dlfcn.h>

#include "doctest/doctest.h"
#include "rogue/hardware/axi/AxiStreamDma.h"
#include "rogue/interfaces/stream/Frame.h"

namespace rha = rogue::hardware::axi;

namespace {

// Sentinel path recognized by the fake_dma_preload LD_PRELOAD shim.
const char* const kFakePath = "/tmp/rogue-fake-datadev";

typedef int (*MappedCountFn)(void);

// Resolve the shim's query hook. Non-null only when the shim is preloaded.
MappedCountFn mappedCountHook() {
    return reinterpret_cast<MappedCountFn>(dlsym(RTLD_DEFAULT, "fakedma_mapped_count"));
}

}  // namespace

TEST_CASE("AxiStreamDma keeps the shared DMA mapping alive across stop()") {
    MappedCountFn mappedCount = mappedCountHook();
    REQUIRE(mappedCount != nullptr);  // fake_dma_preload shim must be LD_PRELOAD'd
    REQUIRE(mappedCount() == 0);

    auto dma = rha::AxiStreamDma::create(kFakePath, 0, false);

    // dmaMapDma() maps all shared zero-copy buffers at construction.
    const int mappedAtCtor = mappedCount();
    REQUIRE(mappedAtCtor > 0);

    // Obtain a zero-copy frame and retain it past stop(); its buffer points
    // into the shared mapping.
    auto frame = dma->acceptReq(4096, true);
    REQUIRE(static_cast<bool>(frame));
    REQUIRE(frame->bufferCount() > 0);

    dma->stop();

    // The fix keeps the shared mapping valid after stop() so the retained frame
    // does not dangle. Reverted code releases it inside stop(), dropping the
    // count to zero here.
    CHECK_EQ(mappedCount(), mappedAtCtor);

    // Returning the buffer post-stop() is a no-op on the driver (fd_ == -1); it
    // must not touch the still-mapped memory or throw.
    frame.reset();
    CHECK_EQ(mappedCount(), mappedAtCtor);

    // Destruction is the single point that releases the shared mapping.
    dma.reset();
    CHECK_EQ(mappedCount(), 0);
}
