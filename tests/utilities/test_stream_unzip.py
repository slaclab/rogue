#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : StreamUnZip regression tests
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
# Covers PR-scoped behaviors of StreamUnZip:
#   * Roundtrip success via StreamZip -> StreamUnZip (exercises BZ2_bzDecompressEnd
#     on the success path).
#   * Truncated bzip2 input (decompressor consumes all input but demands more)
#     must raise the new bound-check exception added in StreamUnZip.cpp.
#   * Garbage bzip2 input (decompressor returns a runtime error) must raise.
#     The new try/catch wrapper is what guarantees BZ2_bzDecompressEnd runs on
#     these throw paths; reverting it does not visibly fail the test, but the
#     test still pins the contract that a runtime error becomes a Python
#     exception rather than silently corrupting the stream.

import bz2
import time

import pytest

import rogue.interfaces.stream
import rogue.utilities


class FrameSink(rogue.interfaces.stream.Slave):
    def __init__(self):
        super().__init__()
        self.frames = []

    def _acceptFrame(self, frame):
        with frame.lock():
            self.frames.append(bytes(frame.getBa()))


class FrameSource(rogue.interfaces.stream.Master):
    def send(self, data):
        frame = self._reqFrame(len(data), True)
        frame.write(bytearray(data))
        self._sendFrame(frame)


def _wait_for(predicate, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def test_stream_unzip_roundtrip():
    """StreamZip -> StreamUnZip must reproduce the original payload."""
    src = FrameSource()
    comp = rogue.utilities.StreamZip()
    decomp = rogue.utilities.StreamUnZip()
    sink = FrameSink()

    src >> comp >> decomp >> sink

    payload = bytes((i * 31 + 7) & 0xFF for i in range(8 * 1024))
    src.send(payload)

    assert _wait_for(lambda: len(sink.frames) == 1), "decompressed frame never arrived"
    assert sink.frames[0] == payload


def test_stream_unzip_truncated_input_raises():
    """A truncated bzip2 stream must raise the new bound-check exception.

    Without the new ``rBuff + 1 == endBuffer()`` guard in StreamUnZip.cpp,
    the iterator is advanced past the last buffer and dereferenced (UB).
    With the guard, a Rogue ``GeneralError`` propagates up through
    ``_sendFrame`` and is observable as a Python exception.
    """
    src = FrameSource()
    decomp = rogue.utilities.StreamUnZip()
    sink = FrameSink()
    src >> decomp >> sink

    # Build a valid bzip2 stream then chop it down to its first few bytes so the
    # decompressor returns BZ_OK with avail_in==0 but is not yet finished. The
    # chop has to be small enough to land in the BZ_OK-but-incomplete region;
    # mid-stream truncations are detected by libbz2 itself as BZ_DATA_ERROR
    # and would route through the unrelated "Decompression runtime error"
    # throw above the bound check.
    valid = bz2.compress(b"X" * 64 * 1024, compresslevel=1)
    truncated = valid[:8]

    with pytest.raises(Exception, match="needs more input than available"):
        src.send(truncated)


def test_stream_unzip_garbage_input_raises():
    """Garbage input must raise instead of silently leaking BZ2 state.

    Reverting the new ``try/catch`` wrapper in StreamUnZip.cpp does not
    visibly fail this test (the leak is only observable under leak
    detectors), but the test does pin the public contract that an invalid
    stream becomes a Python exception.
    """
    src = FrameSource()
    decomp = rogue.utilities.StreamUnZip()
    sink = FrameSink()
    src >> decomp >> sink

    with pytest.raises(Exception):
        src.send(b"\x00" * 256)


def _mallinfo2_uordblks() -> int | None:
    """Return ``mallinfo2().uordblks`` (in-use bytes) or ``None`` if unavailable."""
    import ctypes
    import ctypes.util
    libc_path = ctypes.util.find_library("c")
    if libc_path is None:
        return None
    libc = ctypes.CDLL(libc_path)
    if not hasattr(libc, "mallinfo2"):
        return None

    class _Mallinfo2(ctypes.Structure):
        _fields_ = [
            ("arena", ctypes.c_size_t),
            ("ordblks", ctypes.c_size_t),
            ("smblks", ctypes.c_size_t),
            ("hblks", ctypes.c_size_t),
            ("hblkhd", ctypes.c_size_t),
            ("usmblks", ctypes.c_size_t),
            ("fsmblks", ctypes.c_size_t),
            ("uordblks", ctypes.c_size_t),
            ("fordblks", ctypes.c_size_t),
            ("keepcost", ctypes.c_size_t),
        ]

    libc.mallinfo2.restype = _Mallinfo2
    return libc.mallinfo2().uordblks


def test_stream_unzip_garbage_input_does_not_leak_bz2_state():
    """The try/catch in StreamUnZip.cpp must call BZ2_bzDecompressEnd on throw.

    Without the wrapper, every garbage frame leaks ~64 KiB of bzip2 internal
    state. Direct measurement via glibc's ``mallinfo2()`` shows this clearly:
    the reverted code grows ``uordblks`` by ~128 MiB over 2000 iterations,
    while the fixed code stays in the low-KiB noise floor. This assertion
    uses a 4 MiB ceiling so 1) Python-level exception churn well below the
    threshold, and 2) the reverted leak (~128 MiB) trips it by ~30x.
    """
    baseline = _mallinfo2_uordblks()
    if baseline is None:
        pytest.skip("mallinfo2 not available on this libc")

    src = FrameSource()
    decomp = rogue.utilities.StreamUnZip()
    sink = FrameSink()
    src >> decomp >> sink

    garbage = b"\x00" * 256

    # Warm-up so any first-use Python/object allocations don't pollute the
    # baseline we measure against.
    for _ in range(50):
        try:
            src.send(garbage)
        except Exception:
            pass

    before = _mallinfo2_uordblks()
    for _ in range(2000):
        try:
            src.send(garbage)
        except Exception:
            pass
    after = _mallinfo2_uordblks()

    delta = after - before
    # Reverted code: ~128 MiB. Fixed code: a few KiB.
    assert delta < 4 * 1024 * 1024, f"BZ2 internal state appears to be leaking: {delta} bytes"
