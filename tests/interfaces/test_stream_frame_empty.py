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

import numpy as np
import rogue.interfaces.stream
import pytest


@pytest.fixture
def empty_frame():
    """Frame with zero buffers, as returned by Pool::acceptReq(0, False)."""
    master = rogue.interfaces.stream.Master()
    frame = master._reqFrame(0, False)
    assert frame.getSize() == 0
    assert frame.getPayload() == 0
    return frame


def test_empty_frame_read(empty_frame):
    # Regression: FrameIterator's begin constructor dereferenced the empty
    # buffer list and segfaulted on a frame with no buffers.
    ba = bytearray()
    empty_frame.read(ba)
    assert ba == bytearray()


def test_empty_frame_get_ba(empty_frame):
    assert empty_frame.getBa() == bytearray()


def test_empty_frame_get_memoryview(empty_frame):
    assert bytes(empty_frame.getMemoryview()) == b''


def test_empty_frame_get_numpy(empty_frame):
    arr = empty_frame.getNumpy()
    assert arr.dtype == np.uint8
    assert arr.size == 0


def test_empty_frame_write(empty_frame):
    empty_frame.write(b'')
    assert empty_frame.getPayload() == 0
