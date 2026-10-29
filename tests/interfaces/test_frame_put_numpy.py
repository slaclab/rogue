#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : stream::Frame putNumpy regression tests
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
#
# Frame::putNumpy() makes a temporary contiguous copy of non-contiguous
# input arrays. The copy must be released on the size-check error path,
# otherwise every oversize write of a sliced or transposed view leaks a
# full copy of the array.

import gc
import tracemalloc

import numpy as np
import pytest

import rogue
import rogue.interfaces.stream


FRAME_SIZE = 64


def _new_frame():
    master = rogue.interfaces.stream.Master()
    return master._reqFrame(FRAME_SIZE, True)


def test_put_numpy_contiguous_round_trip():
    frame = _new_frame()
    data = np.arange(FRAME_SIZE, dtype=np.uint8)

    frame.putNumpy(data, 0)

    assert frame.getPayload() == FRAME_SIZE
    assert np.array_equal(frame.getNumpy(0, FRAME_SIZE), data)


def test_put_numpy_non_contiguous_round_trip():
    frame = _new_frame()
    base = np.arange(2 * FRAME_SIZE, dtype=np.uint8)
    view = base[::2]
    assert not view.flags['C_CONTIGUOUS']

    frame.putNumpy(view, 0)

    assert frame.getPayload() == FRAME_SIZE
    assert np.array_equal(frame.getNumpy(0, FRAME_SIZE), view)


def test_put_numpy_oversize_non_contiguous_raises():
    frame = _new_frame()
    view = np.zeros((4, 1024), np.uint8)[:, ::2]
    assert not view.flags['C_CONTIGUOUS']
    assert view.nbytes > FRAME_SIZE

    with pytest.raises(rogue.GeneralError):
        frame.putNumpy(view, 0)


def test_put_numpy_oversize_non_contiguous_does_not_leak():
    frame = _new_frame()
    # 256 KiB per temporary copy so a leak is well above allocator noise.
    view = np.zeros((256, 2048), np.uint8)[:, ::2]
    assert not view.flags['C_CONTIGUOUS']
    copy_bytes = view.nbytes
    iterations = 50

    def attempt():
        with pytest.raises(rogue.GeneralError):
            frame.putNumpy(view, 0)

    # Warm up so any one-time allocations are excluded from the measurement.
    attempt()
    gc.collect()

    tracemalloc.start()
    try:
        before, _ = tracemalloc.get_traced_memory()
        for _ in range(iterations):
            attempt()
        gc.collect()
        after, _ = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    growth = after - before
    # A leak would grow by roughly copy_bytes per iteration.
    assert growth < copy_bytes, (
        f"putNumpy leaked {growth} bytes over {iterations} oversize writes "
        f"({copy_bytes} bytes per temporary copy)")
