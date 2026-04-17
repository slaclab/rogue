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

from pyrogue.utilities.prbs import PrbsRx, PrbsTx, PrbsPair

from conftest import wait_for


class PrbsDeviceRoot(pr.Root):
    def __init__(self, **kwargs):
        super().__init__(name='root', pollEn=False, **kwargs)


def test_prbs_rx_device_tree():
    root = PrbsDeviceRoot()
    root.add(PrbsRx(name='Rx'))
    with root:
        dev = root.Rx
        expected = ['rxEnable', 'rxErrors', 'rxCount', 'rxBytes',
                    'rxRate', 'rxBw', 'checkPayload']
        for var_name in expected:
            assert dev.node(var_name) is not None, f"Missing variable: {var_name}"


def test_prbs_tx_device_tree():
    root = PrbsDeviceRoot()
    root.add(PrbsTx(name='Tx'))
    with root:
        dev = root.Tx
        expected = ['txSize', 'txPeriod', 'txEnable', 'txErrors',
                    'txCount', 'txBytes', 'genPayload', 'txRate', 'txBw']
        for var_name in expected:
            assert dev.node(var_name) is not None, f"Missing variable: {var_name}"


def test_prbs_pair_device_tree():
    root = PrbsDeviceRoot()
    root.add(PrbsPair(name='Pair'))
    with root:
        assert root.Pair.PrbsTx is not None
        assert root.Pair.PrbsRx is not None


def test_prbs_pair_loopback():
    fifo = rogue.interfaces.stream.Fifo(100, 0, False)
    root = PrbsDeviceRoot()
    root.add(PrbsTx(name='Tx', stream=fifo))
    root.add(PrbsRx(name='Rx', stream=fifo))

    with root:
        root.Tx.genFrame.call(5)
        assert wait_for(lambda: root.Rx.rxCount.get() >= 5, timeout=5.0)
        assert root.Rx.rxErrors.get() == 0


def test_prbs_tx_gen_frame_command():
    fifo = rogue.interfaces.stream.Fifo(100, 0, False)
    root = PrbsDeviceRoot()
    root.add(PrbsTx(name='Tx', stream=fifo))

    rx = rogue.utilities.Prbs()
    rx.checkPayload(True)
    fifo >> rx

    with root:
        root.Tx.genFrame.call(3)
        assert wait_for(lambda: rx.getRxCount() == 3, timeout=5.0)
        assert rx.getRxErrors() == 0


def test_prbs_rx_width_set():
    root = PrbsDeviceRoot()
    root.add(PrbsRx(name='Rx', width=64))
    with root:
        pass


def test_prbs_tx_width_set():
    root = PrbsDeviceRoot()
    root.add(PrbsTx(name='Tx', width=64))
    with root:
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
