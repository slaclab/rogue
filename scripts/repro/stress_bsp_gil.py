#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""
DETECTED-IDs:
  - HW-CORE-016
  - HW-CORE-006

Stress the Bsp GIL-less Python-access pattern (HW-CORE-016) and the
AxiStreamDma::sharedBuffers_ static std::map concurrent-modification race
(HW-CORE-006).

HW-CORE-016 : Bsp methods call Boost.Python without the GIL held, so the
C++-side ref counting stomps CPython's internal refcount state. Python
GIL still protects single-instruction bumps, but repeated access from
many threads stresses the pattern.

HW-CORE-006 : Two concurrent AxiStreamDma constructions mutate the static
sharedBuffers_ std::map without locking. Only triggerable on systems with
/dev/axi_stream_dma_0; gracefully skips in CI without the device.
"""
import os
import threading

import pyrogue as pr
import pytest
import rogue

pytestmark = pytest.mark.repro


class _BspProbe(pr.Device):
    """Minimal Device with a few local variables for Bsp attribute churn."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for i in range(4):
            self.add(pr.LocalVariable(
                name=f"Value{i}",
                value=i,
                mode="RW",
            ))


@pytest.mark.repro
def test_stress_bsp_gilless_attribute(stress_iters):
    """Bsp attribute access from many Python threads exercises GIL-less Boost.Python path (HW-CORE-016)."""
    errors = []

    root = pr.Root(name="bsp_root", pollEn=False)
    root.add(_BspProbe(name="probe"))
    with root:
        bsp = rogue.interfaces.api.Bsp(root)

        def accessor(i):
            for j in range(stress_iters // 10):
                try:
                    # Bsp getAttribute runs through the Boost.Python bridge;
                    # under heavy cross-thread access this exercises the
                    # refcount-without-GIL pattern HW-CORE-016 flags.
                    _ = bsp.getAttribute(f"probe.Value{j % 4}")
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=accessor, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    assert not errors, f"Bsp GIL-less stress errors: {errors}"


@pytest.mark.repro
def test_stress_sharedbuffers_map_race(stress_iters):
    """AxiStreamDma::sharedBuffers_ static std::map concurrent modification (HW-CORE-006).

    Only triggerable on systems with /dev/axi_stream_dma_0 present.
    Gracefully skips in CI.
    """
    if not os.path.exists("/dev/axi_stream_dma_0"):
        pytest.skip("no AxiStreamDma hardware device present")
    errors = []

    def ctor_cycle():
        for _ in range(stress_iters // 10):
            try:
                d = rogue.hardware.axi.AxiStreamDma("/dev/axi_stream_dma_0", 0, True)
                del d
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=ctor_cycle) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"sharedBuffers_ map-race stress errors: {errors}"
