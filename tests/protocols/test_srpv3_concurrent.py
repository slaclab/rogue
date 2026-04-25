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
#
# Concurrent SRPv3 transaction tests and diagnostic validation.
#
# These tests exercise the SRPv3 protocol under concurrent load and
# validate that error messages include sufficient diagnostic detail
# for field troubleshooting.
#
# test_srpv3_header_mismatch_error_includes_diagnostics: FAILS on
# unpatched code because the "did not match expected protocol" error
# string is generic. After the fix, it includes the transaction id and
# target address so the offending transaction can be identified in the
# field. Corrupting header word 4 trips the protocol-header comparison
# before the size-mismatch check (see SrpV3::acceptFrame ordering).

import struct
import threading

import pyrogue as pr
import pyrogue.interfaces.simulation
import rogue
import rogue.interfaces.stream
import rogue.protocols.srp
import pytest

pytestmark = pytest.mark.integration


class SrpV3ConcurrentDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for i in range(8):
            self.add(pr.RemoteVariable(
                name=f'Reg{i}',
                offset=0x04 * i,
                bitSize=32,
                mode='RW',
                base=pr.UInt,
            ))


class SrpV3ConcurrentRoot(pr.Root):
    def __init__(self, **kwargs):
        super().__init__(
            name='SrpV3ConcRoot',
            description='SrpV3 concurrent transaction test',
            timeout=2.0,
            pollEn=False,
            **kwargs,
        )
        self.srp = rogue.protocols.srp.SrpV3()
        self.srpServer = rogue.protocols.srp.SrpV3Emulation()
        self.srp == self.srpServer

        for i in range(4):
            self.add(SrpV3ConcurrentDevice(
                name=f'Dev[{i}]',
                offset=i * 0x10000,
                memBase=self.srp,
            ))


class TimeoutMemEmulate(pr.interfaces.simulation.MemEmulate):
    """Memory emulator that drops a configurable number of transactions."""

    def __init__(self, *, dropCount=0, **kwargs):
        super().__init__(**kwargs)
        self._dropTotal = dropCount
        self._dropped = 0

    def _doTransaction(self, transaction):
        if self._dropped < self._dropTotal:
            self._dropped += 1
            return
        super()._doTransaction(transaction)


class TimeoutDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for i in range(4):
            self.add(pr.RemoteVariable(
                name=f'Reg{i}',
                offset=0x04 * i,
                bitSize=32,
                base=pr.UInt,
                mode='RW',
            ))


def test_srpv3_header_mismatch_error_includes_diagnostics():
    """The protocol-header mismatch error must include diagnostic detail.

    On unpatched code, the error is the generic string:
      "Received SRPV3 message did not match expected protocol"
    After the fix, it includes the transaction id= and addr= so the
    offending transaction can be traced.

    Strategy: set up an SrpV3 client with SrpV3Emulation, start a read
    transaction for 4 bytes (1 word), then intercept the emulation
    response and corrupt header word 4 (request-size field) before it
    reaches the SrpV3 client. In SrpV3::acceptFrame the protocol-header
    comparison runs BEFORE the size-mismatch check, and it compares
    header[0..4] against expected values — so corrupting header[4]
    reliably trips the protocol-mismatch path, which carries the
    id=/addr= diagnostics this test validates.
    """
    srp_client = rogue.protocols.srp.SrpV3()
    srp_server = rogue.protocols.srp.SrpV3Emulation()

    # We need to intercept responses.  Insert a frame corruptor between
    # the server and client.
    class HeaderCorruptor(rogue.interfaces.stream.Slave,
                          rogue.interfaces.stream.Master):
        """Intercept frames and corrupt SRPv3 header word 4 so the
        protocol-header compare rejects the response."""
        def __init__(self):
            rogue.interfaces.stream.Slave.__init__(self)
            rogue.interfaces.stream.Master.__init__(self)
            self.corrupt_next = False

        def _acceptFrame(self, frame):
            ba = bytearray(frame.getBa())
            if self.corrupt_next and len(ba) >= 20:
                # Corrupt header word 4 (request-size field). This field
                # is part of the protocol-header compare, so mutating it
                # trips the "did not match expected protocol" branch
                # before the size-mismatch check is reached.
                orig_size = struct.unpack_from('<I', ba, 16)[0]
                struct.pack_into('<I', ba, 16, orig_size + 99)
                self.corrupt_next = False
            new_frame = self._reqFrame(len(ba), True)
            new_frame.write(ba)
            self._sendFrame(new_frame)

    corruptor = HeaderCorruptor()

    # Wire: srp_client -> srp_server -> corruptor -> srp_client
    srp_client >> srp_server
    srp_server >> corruptor
    corruptor >> srp_client

    dev = pr.Device(name='Dev', offset=0x0, memBase=srp_client)
    dev.add(pr.RemoteVariable(
        name='Reg0', offset=0x0, bitSize=32, mode='RW', base=pr.UInt,
    ))

    root = pr.Root(
        name='HeaderMismatchRoot',
        timeout=1.0,
        pollEn=False,
    )
    root.add(dev)
    root.start()
    try:
        # First do a normal write so the emulation has data
        root.Dev.Reg0.set(0xDEAD)

        # Now corrupt the next response
        corruptor.corrupt_next = True

        with pytest.raises(rogue.GeneralError) as exc_info:
            root.Dev.Reg0.get()

        err_msg = str(exc_info.value)

        # The error must contain diagnostic fields — not just the
        # generic message. Corrupting header[4] trips the protocol-
        # header compare (which runs before the size-mismatch check),
        # and that path, after the fix, includes id= and addr=.
        assert "id=" in err_msg and "addr=" in err_msg, (
            f"Error lacks diagnostic detail (id/addr). "
            f"Got: {err_msg!r}"
        )
    finally:
        root.stop()


def test_srpv3_concurrent_reads_no_crosstalk():
    """Read registers from 4 devices concurrently; verify no cross-talk."""
    ITERATIONS = 100
    errors = []

    with SrpV3ConcurrentRoot() as root:
        for i in range(4):
            for r in range(8):
                root.Dev[i].node(f'Reg{r}').set(0x1000 * i + r, write=True)

        def reader(dev_idx):
            try:
                for _ in range(ITERATIONS):
                    for r in range(8):
                        val = root.Dev[dev_idx].node(f'Reg{r}').get()
                        expected = 0x1000 * dev_idx + r
                        if val != expected:
                            errors.append(
                                f"Dev[{dev_idx}].Reg{r}: "
                                f"got 0x{val:08x}, expected 0x{expected:08x}"
                            )
            except Exception as e:
                errors.append(f"Dev[{dev_idx}] exception: {e}")

        threads = []
        for i in range(4):
            t = threading.Thread(target=reader, args=(i,), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=30)

        for t in threads:
            assert not t.is_alive(), f"Thread {t.name} hung"

    assert errors == [], (
        "Concurrent SRP cross-talk detected:\n"
        + "\n".join(errors[:10])
    )


def test_srpv3_late_response_after_timeout():
    """A transaction that times out must not leave the system stuck."""
    class LateResponseRoot(pr.Root):
        def __init__(self):
            super().__init__(
                name='lateRespRoot',
                description='Late response test',
                timeout=0.01,
                pollEn=False,
            )
            sim = TimeoutMemEmulate(dropCount=1)
            self.addInterface(sim)
            self.add(TimeoutDevice(
                name='Dev', offset=0x0, memBase=sim,
            ))

    root = LateResponseRoot()
    root.start()
    try:
        with pytest.raises(rogue.GeneralError, match="Timeout"):
            root.Dev.Reg0.get()

        root.Dev.Reg1.set(0xBEEF)
        val = root.Dev.Reg1.get()
        assert val == 0xBEEF, (
            f"System stuck after timeout: got 0x{val:08x}"
        )
    finally:
        root.stop()


def test_srpv3_concurrent_write_read_integrity():
    """Concurrent writes and reads must not corrupt each other."""
    ITERATIONS = 50
    errors = []

    with SrpV3ConcurrentRoot() as root:
        def writer(dev_idx):
            try:
                for i in range(ITERATIONS):
                    for r in range(8):
                        root.Dev[dev_idx].node(f'Reg{r}').set(
                            0x100 * dev_idx + 0x10 * r + (i & 0xF),
                            write=True,
                        )
            except Exception as e:
                errors.append(f"Writer Dev[{dev_idx}]: {e}")

        def reader(dev_idx):
            try:
                for _ in range(ITERATIONS):
                    for r in range(8):
                        root.Dev[dev_idx].node(f'Reg{r}').get()
            except Exception as e:
                errors.append(f"Reader Dev[{dev_idx}]: {e}")

        threads = []
        for i in range(4):
            tw = threading.Thread(
                target=writer, args=(i,), daemon=True)
            tr = threading.Thread(
                target=reader, args=(i,), daemon=True)
            threads.extend([tw, tr])
            tw.start()
            tr.start()

        for t in threads:
            t.join(timeout=30)

        for t in threads:
            assert not t.is_alive(), f"Thread {t.name} hung"

    assert errors == [], (
        "Concurrent write/read errors:\n"
        + "\n".join(errors[:10])
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
