#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import rogue
import rogue.protocols.packetizer
import rogue.utilities
import pytest

from conftest import wait_for

pytestmark = pytest.mark.integration

DRAIN_TIMEOUT = 5.0


def _make_packetizer_pair():
    """Create two V1 Packetizer cores wired transport-to-transport."""
    core_a = rogue.protocols.packetizer.Core(True)
    core_b = rogue.protocols.packetizer.Core(True)

    core_a.transport() == core_b.transport()

    return core_a, core_b


def test_packetizer_v1_single_dest_frame_delivery():
    core_a, core_b = _make_packetizer_pair()

    tx = rogue.utilities.Prbs()
    rx = rogue.utilities.Prbs()
    rx.checkPayload(True)

    core_a.application(0) << tx
    rx << core_b.application(0)

    for _ in range(20):
        tx.genFrame(256)

    assert wait_for(lambda: rx.getRxCount() == 20, timeout=DRAIN_TIMEOUT)
    assert rx.getRxErrors() == 0


def test_packetizer_v1_multi_dest_routing():
    core_a, core_b = _make_packetizer_pair()

    tx0 = rogue.utilities.Prbs()
    rx0 = rogue.utilities.Prbs()
    tx1 = rogue.utilities.Prbs()
    rx1 = rogue.utilities.Prbs()

    rx0.checkPayload(True)
    rx1.checkPayload(True)

    core_a.application(0) << tx0
    rx0 << core_b.application(0)

    core_a.application(1) << tx1
    rx1 << core_b.application(1)

    for _ in range(10):
        tx0.genFrame(128)
    for _ in range(15):
        tx1.genFrame(128)

    assert wait_for(lambda: rx0.getRxCount() == 10, timeout=DRAIN_TIMEOUT)
    assert wait_for(lambda: rx1.getRxCount() == 15, timeout=DRAIN_TIMEOUT)

    assert rx0.getRxErrors() == 0
    assert rx1.getRxErrors() == 0


def test_packetizer_v1_large_frame_fragmentation():
    core_a, core_b = _make_packetizer_pair()

    tx = rogue.utilities.Prbs()
    rx = rogue.utilities.Prbs()
    rx.checkPayload(True)

    core_a.application(0) << tx
    rx << core_b.application(0)

    tx.genFrame(8192)

    assert wait_for(lambda: rx.getRxCount() == 1, timeout=DRAIN_TIMEOUT)
    assert rx.getRxErrors() == 0


def test_packetizer_v1_drop_count_initially_zero():
    core = rogue.protocols.packetizer.Core(True)
    assert core.getDropCount() == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
