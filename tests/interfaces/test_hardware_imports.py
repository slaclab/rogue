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

import pytest

# rogue.hardware requires the AXI DMA kernel driver headers at build
# time and is only compiled on Linux.  On macOS the submodule is absent.
try:
    import rogue
    import rogue.hardware
    import rogue.hardware.axi
except Exception as exc:
    pytest.skip(
        f"rogue.hardware not available: {exc}",
        allow_module_level=True,
    )


def test_import_memmap():
    assert hasattr(rogue.hardware, 'MemMap')


def test_import_axi_memmap():
    assert hasattr(rogue.hardware.axi, 'AxiMemMap')


def test_import_axi_stream_dma():
    assert hasattr(rogue.hardware.axi, 'AxiStreamDma')
