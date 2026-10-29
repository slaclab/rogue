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

import contextlib
import queue
import sys
import types

import pyrogue
import rogue.interfaces.memory

# pyrogue.protocols.gpib does ``from gpib_ctypes import Gpib`` at module
# level.  That package (pip install gpib-ctypes) wraps linux-gpib, which
# requires a physical GPIB interface and the linux-gpib kernel driver.
# Neither is present in CI or on most developer machines.  When the real
# package is missing, install a minimal stub into sys.modules so the module
# under test imports.  The tests below never call GpibController.__init__,
# so no GPIB hardware is touched whether the stub or the real package is
# present.
try:
    import gpib_ctypes  # noqa: F401
except Exception:
    _gpib_stub = types.ModuleType("gpib_ctypes.Gpib")
    _gpib_stub.gpib = types.SimpleNamespace(T1s=11)
    _gpib_stub.Gpib = object
    _pkg_stub = types.ModuleType("gpib_ctypes")
    _pkg_stub.Gpib = _gpib_stub
    sys.modules["gpib_ctypes"] = _pkg_stub
    sys.modules["gpib_ctypes.Gpib"] = _gpib_stub

from pyrogue.protocols.gpib import GpibController, GpibDevice  # noqa: E402


class FakeGpib:
    """Scripted GPIB bus: each read() pops the next queued reply or exception."""

    def __init__(self):
        self.writes = []
        self.replies = []

    def write(self, payload):
        self.writes.append(payload)

    def read(self, _length):
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


class FakeVariable:
    def __init__(self, *, offset, key, bitSize=32):
        self.offset = offset
        self._key = key
        self.base = pyrogue.UInt(bitSize)

    def getExtraAttribute(self, name):
        return self._key if name == 'key' else None

    def genDisp(self, value):
        return str(value)

    def parseDisp(self, text):
        return int(text)


class FakeTransaction:
    def __init__(self, *, address, size, tx_type, payload=None):
        self._address = address
        self._size = size
        self._type = tx_type
        self._payload = bytearray(payload or bytes(size))
        self.errors = []
        self.done_called = False
        self.readback = bytearray(size)

    def address(self):
        return self._address

    def size(self):
        return self._size

    def type(self):
        return self._type

    def getData(self, buffer, offset):
        buffer[:] = self._payload[offset:offset + len(buffer)]

    def setData(self, buffer, offset):
        self.readback[offset:offset + len(buffer)] = buffer

    def done(self):
        self.done_called = True

    def error(self, msg):
        self.errors.append(msg)

    def lock(self):
        return contextlib.nullcontext()


def make_controller(fake_gpib, variables):
    """Build a GpibController without touching hardware (skips __init__)."""
    ctrl = GpibController.__new__(GpibController)
    ctrl._log = pyrogue.logInit(name="test-gpib")
    ctrl._gpib = fake_gpib
    ctrl._workerQueue = queue.Queue()
    ctrl._workerThread = None
    ctrl._map = {v.offset: v for v in variables}
    return ctrl


def test_gpib_controller_class_exists():
    assert GpibController is not None


def test_gpib_device_class_exists():
    assert GpibDevice is not None


def test_gpib_worker_survives_read_exception():
    fake_gpib = FakeGpib()
    var = FakeVariable(offset=0x0, key="VOLT")
    ctrl = make_controller(fake_gpib, [var])

    # First read raises inside the worker (e.g. a GPIB bus timeout); the
    # second read must still be served by the same worker loop.
    fake_gpib.replies = [RuntimeError("bus timeout"), b"42\n"]

    bad_tx = FakeTransaction(address=0x0, size=4, tx_type=rogue.interfaces.memory.Read)
    good_tx = FakeTransaction(address=0x0, size=4, tx_type=rogue.interfaces.memory.Read)

    ctrl._workerQueue.put(bad_tx)
    ctrl._workerQueue.put(good_tx)
    ctrl._workerQueue.put(None)
    ctrl._worker()

    assert not bad_tx.done_called
    assert len(bad_tx.errors) == 1
    assert "Unhandled GPIB worker exception" in bad_tx.errors[0]
    assert "bus timeout" in bad_tx.errors[0]

    assert good_tx.done_called is True
    assert good_tx.errors == []
    assert bytes(good_tx.readback) == (42).to_bytes(4, 'little')
    assert fake_gpib.writes == [b"VOLT?", b"VOLT?"]


def test_gpib_worker_write_and_error_paths():
    fake_gpib = FakeGpib()
    var = FakeVariable(offset=0x4, key="CURR")
    ctrl = make_controller(fake_gpib, [var])

    write_tx = FakeTransaction(
        address=0x4,
        size=4,
        tx_type=rogue.interfaces.memory.Write,
        payload=(7).to_bytes(4, 'little'),
    )
    unknown_tx = FakeTransaction(address=0x100, size=4, tx_type=rogue.interfaces.memory.Read)
    size_tx = FakeTransaction(address=0x4, size=2, tx_type=rogue.interfaces.memory.Read)
    post_tx = FakeTransaction(address=0x4, size=4, tx_type=rogue.interfaces.memory.Post)

    for tx in (write_tx, unknown_tx, size_tx, post_tx, None):
        ctrl._workerQueue.put(tx)
    ctrl._worker()

    assert write_tx.done_called is True
    assert fake_gpib.writes == [b"CURR 7"]
    assert "Unknown address" in unknown_tx.errors[0]
    assert "Transaction size mismatch" in size_tx.errors[0]
    assert "Unsupported transaction type" in post_tx.errors[0]
