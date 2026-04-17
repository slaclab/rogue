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

import pyrogue as pr
import rogue
import rogue.interfaces.stream
import rogue.utilities
import pytest

from pyrogue.interfaces.stream import Fifo

from conftest import wait_for


class FifoTestRoot(pr.Root):
    def __init__(self, **kwargs):
        super().__init__(name='root', pollEn=False, **kwargs)


def test_fifo_device_variables():
    root = FifoTestRoot()
    root.add(Fifo(name='TestFifo', maxDepth=100))

    with root:
        dev = root.TestFifo
        assert dev.node('MaxDepth') is not None
        assert dev.node('Size') is not None
        assert dev.node('FrameDropCnt') is not None
        assert dev.node('ClearCnt') is not None

        assert dev.MaxDepth.get() == 100


def test_fifo_device_frame_flow():
    root = FifoTestRoot()
    root.add(Fifo(name='TestFifo', maxDepth=200))

    tx = rogue.utilities.Prbs()
    rx = rogue.utilities.Prbs()
    rx.checkPayload(True)

    with root:
        tx >> root.TestFifo >> rx

        for _ in range(20):
            tx.genFrame(256)

        assert wait_for(lambda: rx.getRxCount() == 20, timeout=5.0)
        assert rx.getRxErrors() == 0


def test_fifo_device_stream_operators():
    root = FifoTestRoot()
    root.add(Fifo(name='TestFifo', maxDepth=50))

    master = rogue.interfaces.stream.Master()
    slave = rogue.interfaces.stream.Slave()

    with root:
        master >> root.TestFifo
        root.TestFifo >> slave


def test_fifo_device_count_reset():
    root = FifoTestRoot()
    root.add(Fifo(name='TestFifo', maxDepth=200))

    tx = rogue.utilities.Prbs()
    rx = rogue.utilities.Prbs()
    rx.checkPayload(True)

    with root:
        tx >> root.TestFifo >> rx

        for _ in range(5):
            tx.genFrame(256)

        assert wait_for(lambda: rx.getRxCount() == 5)

        root.TestFifo.countReset()
        assert root.TestFifo.FrameDropCnt.get() == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
