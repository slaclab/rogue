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

from types import SimpleNamespace

import pyrogue as pr
import pytest

# pyrogue.hardware is only available on Linux where the AXI DMA kernel
# driver (aes-stream-drivers) can be built.  On macOS the entire
# pyrogue.hardware subpackage is absent, so we skip gracefully.
try:
    from pyrogue.hardware.axi._AxiStreamDmaMon import (
        AxiStreamDmaMon,
        AxiStreamDmaMonRx,
        AxiStreamDmaMonTx,
    )
except Exception as exc:
    pytest.skip(
        f"pyrogue.hardware not available: {exc}",
        allow_module_level=True,
    )


def _make_mock_dma():
    """Create a mock DMA object with the methods used by the monitor classes."""
    return SimpleNamespace(
        getRxBuffCount=lambda: 128,
        getRxBuffinUserCount=lambda: 10,
        getRxBuffinHwCount=lambda: 50,
        getRxBuffinPreHwQCount=lambda: 5,
        getRxBuffinSwQCount=lambda: 3,
        getRxBuffMissCount=lambda: 0,
        getTxBuffCount=lambda: 64,
        getTxBuffinUserCount=lambda: 8,
        getTxBuffinHwCount=lambda: 30,
        getTxBuffinPreHwQCount=lambda: 2,
        getTxBuffinSwQCount=lambda: 1,
        getTxBuffMissCount=lambda: 0,
        getGitVersion=lambda: 'abc123',
        getApiVersion=lambda: 5,
        getBuffSize=lambda: 0x20000,
    )


def test_dma_mon_rx_variables():
    mock = _make_mock_dma()
    root = pr.Root(name='root', pollEn=False)
    root.add(AxiStreamDmaMonRx(name='Rx', axiStreamDma=mock))

    with root:
        dev = root.Rx
        assert dev.BuffCount.get() == 128
        assert dev.BuffinUserCount.get() == 10
        assert dev.BuffinHwCount.get() == 50
        assert dev.BuffinPreHwQCount.get() == 5
        assert dev.BuffinSwQCount.get() == 3
        assert dev.BuffMissCount.get() == 0


def test_dma_mon_tx_variables():
    mock = _make_mock_dma()
    root = pr.Root(name='root', pollEn=False)
    root.add(AxiStreamDmaMonTx(name='Tx', axiStreamDma=mock))

    with root:
        dev = root.Tx
        assert dev.BuffCount.get() == 64
        assert dev.BuffinUserCount.get() == 8
        assert dev.BuffinHwCount.get() == 30
        assert dev.BuffinPreHwQCount.get() == 2
        assert dev.BuffinSwQCount.get() == 1
        assert dev.BuffMissCount.get() == 0


def test_dma_mon_full_tree():
    mock = _make_mock_dma()
    root = pr.Root(name='root', pollEn=False)
    root.add(AxiStreamDmaMon(name='Mon', axiStreamDma=mock))

    with root:
        dev = root.Mon
        assert dev.GitVersion.get() == 'abc123'
        assert dev.ApiVersion.get() == 5
        assert dev.BuffSize.get() == 0x20000

        assert dev.Rx.BuffCount.get() == 128
        assert dev.Tx.BuffCount.get() == 64


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
