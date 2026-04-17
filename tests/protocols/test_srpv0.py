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

import struct
import time

import pyrogue as pr
import rogue.interfaces.memory
import rogue.interfaces.stream
import rogue.protocols.srp
import pytest


class FrameCapture(rogue.interfaces.stream.Slave):
    """Collect frames emitted by SrpV0."""

    def __init__(self):
        super().__init__()
        self.frames = []

    def _acceptFrame(self, frame):
        self.frames.append(bytes(frame.getBa()))


class SrpV0Responder(rogue.interfaces.stream.Slave, rogue.interfaces.stream.Master):
    """Loopback that mimics SRP v0 hardware for reads and writes.

    A Fifo must be placed between this responder's output and SrpV0's
    input to avoid reentrancy deadlocks (doTransaction holds a lock
    that acceptFrame also needs).
    """

    def __init__(self):
        rogue.interfaces.stream.Slave.__init__(self)
        rogue.interfaces.stream.Master.__init__(self)
        self._mem = {}

    def _acceptFrame(self, frame):
        data = bytes(frame.getBa())
        if len(data) < 12:
            return

        hdr0, hdr1 = struct.unpack_from('<II', data, 0)
        txn_id = hdr0
        is_write = bool(hdr1 & 0x40000000)
        addr = (hdr1 & 0x3FFFFFFF) << 2

        if is_write:
            payload = data[8:-4]
            for i, b in enumerate(payload):
                self._mem[addr + i] = b
            resp = struct.pack('<II', txn_id, hdr1) + payload + b'\x00' * 4
        else:
            hdr2 = struct.unpack_from('<I', data, 8)[0]
            nbytes = (hdr2 + 1) * 4
            payload = bytearray(nbytes)
            for i in range(nbytes):
                payload[i] = self._mem.get(addr + i, 0)
            resp = struct.pack('<II', txn_id, hdr1) + bytes(payload) + b'\x00' * 4

        resp_frame = self._reqFrame(len(resp), True)
        resp_frame.write(resp)
        self._sendFrame(resp_frame)


class SrpV0TestDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add(pr.RemoteVariable(
            name='ScratchPad', offset=0x0000,
            bitSize=32, mode='RW', base=pr.UInt))
        self.add(pr.RemoteVariable(
            name='Register1', offset=0x0004,
            bitSize=32, mode='RW', base=pr.UInt))
        self.add(pr.RemoteVariable(
            name='WideReg', offset=0x0010,
            bitSize=64, mode='RW', base=pr.UInt))


class SrpV0TestRoot(pr.Root):
    def __init__(self, **kwargs):
        super().__init__(
            name='SrpV0TestRoot', timeout=2.0, pollEn=False, **kwargs)

        self.srp = rogue.protocols.srp.SrpV0()
        self.responder = SrpV0Responder()

        # Use a Fifo to break the reentrancy between doTransaction
        # and acceptFrame; the Fifo's internal thread delivers the
        # response asynchronously.
        self._respFifo = rogue.interfaces.stream.Fifo(100, 0, False)

        self.srp >> self.responder
        self.responder >> self._respFifo >> self.srp

        self.add(SrpV0TestDevice(
            name='Dev', offset=0x00000000, memBase=self.srp))


def test_srpv0_basic_write_read():
    with SrpV0TestRoot() as root:
        root.Dev.ScratchPad.set(0xDEADBEEF)
        assert root.Dev.ScratchPad.get() == 0xDEADBEEF


def test_srpv0_multiple_registers():
    with SrpV0TestRoot() as root:
        root.Dev.ScratchPad.set(0x12345678)
        root.Dev.Register1.set(0xAABBCCDD)
        assert root.Dev.ScratchPad.get() == 0x12345678
        assert root.Dev.Register1.get() == 0xAABBCCDD


def test_srpv0_overwrite():
    with SrpV0TestRoot() as root:
        root.Dev.ScratchPad.set(0x11111111)
        assert root.Dev.ScratchPad.get() == 0x11111111
        root.Dev.ScratchPad.set(0x22222222)
        assert root.Dev.ScratchPad.get() == 0x22222222


def test_srpv0_wide_register():
    with SrpV0TestRoot() as root:
        root.Dev.WideReg.set(0x0102030405060708)
        assert root.Dev.WideReg.get() == 0x0102030405060708


def test_srpv0_zero_write():
    with SrpV0TestRoot() as root:
        root.Dev.ScratchPad.set(0xFFFFFFFF)
        assert root.Dev.ScratchPad.get() == 0xFFFFFFFF
        root.Dev.ScratchPad.set(0x00000000)
        assert root.Dev.ScratchPad.get() == 0x00000000


def test_srpv0_write_stores_in_responder():
    """Verify that SrpV0 correctly serializes write data.

    We check the responder's internal memory after a write round-trip.
    """
    with SrpV0TestRoot() as root:
        root.Dev.ScratchPad.set(0xCAFEBABE)

        # The responder's memory should hold the written bytes at offset 0
        mem = root.responder._mem
        val = struct.unpack('<I', bytes(mem.get(i, 0) for i in range(4)))[0]
        assert val == 0xCAFEBABE


def test_srpv0_errored_frame_dropped():
    srp = rogue.protocols.srp.SrpV0()
    inject = rogue.interfaces.stream.Master()
    capture = FrameCapture()
    inject >> srp
    srp >> capture

    frame = inject._reqFrame(16, True)
    ba = bytearray(16)
    frame.write(ba)
    frame.setError(1)
    inject._sendFrame(frame)

    time.sleep(0.1)
    assert len(capture.frames) == 0


def test_srpv0_undersized_frame_dropped():
    srp = rogue.protocols.srp.SrpV0()
    inject = rogue.interfaces.stream.Master()
    capture = FrameCapture()
    inject >> srp
    srp >> capture

    frame = inject._reqFrame(8, True)
    ba = bytearray(8)
    frame.write(ba)
    inject._sendFrame(frame)

    time.sleep(0.1)
    assert len(capture.frames) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
