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
import rogue.utilities
import pytest

from conftest import wait_for


def test_prbs_gen_check_default_width():
    tx = rogue.utilities.Prbs()
    rx = rogue.utilities.Prbs()
    tx >> rx
    rx.checkPayload(True)

    tx.genFrame(1024)
    assert wait_for(lambda: rx.getRxCount() == 1)
    assert rx.getRxErrors() == 0


def test_prbs_multiple_frames():
    tx = rogue.utilities.Prbs()
    rx = rogue.utilities.Prbs()
    tx >> rx
    rx.checkPayload(True)

    count = 100
    for _ in range(count):
        tx.genFrame(256)

    assert wait_for(lambda: rx.getRxCount() == count, timeout=5.0)
    assert rx.getRxErrors() == 0


@pytest.mark.parametrize("width", [32, 64, 128])
def test_prbs_width_variations(width):
    tx = rogue.utilities.Prbs()
    rx = rogue.utilities.Prbs()
    tx.setWidth(width)
    rx.setWidth(width)
    tx >> rx
    rx.checkPayload(True)

    byte_width = width // 8
    frame_size = byte_width * 16

    for _ in range(10):
        tx.genFrame(frame_size)

    assert wait_for(lambda: rx.getRxCount() == 10, timeout=5.0)
    assert rx.getRxErrors() == 0


def test_prbs_counter_mode():
    tx = rogue.utilities.Prbs()
    rx = rogue.utilities.Prbs()
    tx.sendCount(True)
    tx >> rx
    rx.checkPayload(False)

    for _ in range(10):
        tx.genFrame(256)

    assert wait_for(lambda: rx.getRxCount() == 10)


def test_prbs_reset_counters():
    tx = rogue.utilities.Prbs()
    rx = rogue.utilities.Prbs()
    tx >> rx
    rx.checkPayload(True)

    for _ in range(5):
        tx.genFrame(256)

    assert wait_for(lambda: rx.getRxCount() == 5)
    assert tx.getTxCount() == 5

    tx.resetCount()
    rx.resetCount()

    assert tx.getTxCount() == 0
    assert rx.getRxCount() == 0
    assert rx.getRxErrors() == 0


def test_prbs_statistics():
    tx = rogue.utilities.Prbs()
    rx = rogue.utilities.Prbs()
    tx >> rx
    rx.checkPayload(True)

    for _ in range(10):
        tx.genFrame(256)

    assert wait_for(lambda: rx.getRxCount() == 10)

    assert tx.getTxCount() == 10
    assert tx.getTxBytes() > 0
    assert rx.getRxBytes() > 0
    assert rx.getRxErrors() == 0


def test_prbs_rx_disable_skips_check():
    tx = rogue.utilities.Prbs()
    rx = rogue.utilities.Prbs()
    tx >> rx
    rx.checkPayload(True)

    # When rxEnable is False, acceptFrame blocks in a busy-wait,
    # so we verify the enable/disable API without sending frames while disabled.
    assert rx.getRxEnable() is True
    rx.setRxEnable(False)
    assert rx.getRxEnable() is False
    rx.setRxEnable(True)
    assert rx.getRxEnable() is True


def test_prbs_background_tx():
    tx = rogue.utilities.Prbs()
    rx = rogue.utilities.Prbs()
    tx >> rx
    rx.checkPayload(True)

    tx.enable(256)
    assert wait_for(lambda: rx.getRxCount() >= 5, timeout=5.0)
    tx.disable()

    assert rx.getRxErrors() == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
