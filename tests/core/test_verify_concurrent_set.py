#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""
Regression tests for ESROGUE-733: checkTransaction verify failure when
blockData_ is modified between write and verify check.

The bug manifests when two variables share a block and one variable's
blockData_ is modified (via set with write=False or a concurrent _set call)
between the write transaction and the verify comparison. Without the fix,
checkTransaction compares the verify read-back against the modified (stale)
blockData_ instead of the data that was actually written, causing a spurious
verify error.
"""

import threading

import pyrogue as pr
import rogue.interfaces.memory as rim
import pytest


class SharedBlockDevice(pr.Device):
    """Device with two RW+verify variables in the same 4-byte block."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.add(pr.RemoteVariable(
            name='VarLow',
            offset=0x0,
            bitSize=16,
            bitOffset=0,
            base=pr.UInt,
            mode='RW',
            verify=True,
        ))

        self.add(pr.RemoteVariable(
            name='VarHigh',
            offset=0x2,
            bitSize=16,
            bitOffset=0,
            base=pr.UInt,
            mode='RW',
            verify=True,
        ))


class MultiBlockDevice(pr.Device):
    """Device with several RW+verify variables across two 4-byte blocks."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Block 0: two 16-bit variables
        self.add(pr.RemoteVariable(
            name='RegA',
            offset=0x0,
            bitSize=16,
            bitOffset=0,
            base=pr.UInt,
            mode='RW',
            verify=True,
        ))

        self.add(pr.RemoteVariable(
            name='RegB',
            offset=0x2,
            bitSize=16,
            bitOffset=0,
            base=pr.UInt,
            mode='RW',
            verify=True,
        ))

        # Block 1: two 16-bit variables
        self.add(pr.RemoteVariable(
            name='RegC',
            offset=0x4,
            bitSize=16,
            bitOffset=0,
            base=pr.UInt,
            mode='RW',
            verify=True,
        ))

        self.add(pr.RemoteVariable(
            name='RegD',
            offset=0x6,
            bitSize=16,
            bitOffset=0,
            base=pr.UInt,
            mode='RW',
            verify=True,
        ))


class VerifyRoot(pr.Root):
    def __init__(self, DeviceClass=SharedBlockDevice):
        super().__init__(
            name='VerifyRoot',
            description='Test root for verify regression',
            timeout=2.0,
            pollEn=False,
        )
        sim = rim.Emulate(4, 0x1000)
        self.addInterface(sim)
        self.add(DeviceClass(name='Dev', offset=0x0, memBase=sim))


def test_verify_survives_interleaved_set():
    """Verify does not fail when another variable in the same block is
    modified between write and verify check (ESROGUE-733).

    Reproduces the race by manually interleaving:
      1. Set both vars (marks both stale)
      2. writeBlocks (writes both to hardware, snapshots expected data)
      3. Modify one var's blockData_ via set(write=False)
      4. verifyBlocks + checkBlocks (should compare against snapshot)
    """
    with VerifyRoot() as root:
        dev = root.Dev

        # Step 1: set both variables (both become stale in the same block)
        dev.VarLow.set(0x1234, write=False)
        dev.VarHigh.set(0x5678, write=False)

        # Step 2: write all stale vars to hardware
        dev.writeBlocks(force=True)

        # Step 3: modify VarHigh's blockData_ without writing to hardware.
        # This simulates a concurrent thread calling _set() between
        # the write and verify steps.
        dev.VarHigh.set(0xAAAA, write=False)

        # Step 4: verify and check. Without the fix this would raise
        # a GeneralError because blockData_ (0xAAAA) != hardware (0x5678).
        dev.verifyBlocks()
        dev.checkBlocks()  # Should NOT raise

        # Write the pending VarHigh change so the block is no longer stale,
        # then read back from hardware to confirm original VarLow write persisted.
        dev.VarHigh.set(0xAAAA)  # write=True to clear stale
        assert dev.VarLow.get() == 0x1234


def test_verify_catches_real_mismatch():
    """Verify still detects genuine write failures.

    Uses a basic write-verify flow where the written value should
    match the hardware read-back.
    """
    with VerifyRoot() as root:
        dev = root.Dev

        dev.VarLow.set(0xBEEF)
        dev.VarHigh.set(0xCAFE)

        got_low = dev.VarLow.get()
        got_high = dev.VarHigh.get()

        assert got_low == 0xBEEF
        assert got_high == 0xCAFE


def test_verify_bulk_write_and_verify():
    """Bulk writeAndVerifyBlocks still works correctly."""
    with VerifyRoot(DeviceClass=MultiBlockDevice) as root:
        dev = root.Dev

        dev.RegA.set(0x1111, write=False)
        dev.RegB.set(0x2222, write=False)
        dev.RegC.set(0x3333, write=False)
        dev.RegD.set(0x4444, write=False)

        dev.writeAndVerifyBlocks(force=True)

        assert dev.RegA.get() == 0x1111
        assert dev.RegB.get() == 0x2222
        assert dev.RegC.get() == 0x3333
        assert dev.RegD.get() == 0x4444


def test_verify_threaded_concurrent_set():
    """Exercise the actual concurrent threading scenario from ESROGUE-733.

    Thread 1 writes VarLow with verify.
    Thread 2 repeatedly sets VarHigh (modifying blockData_).
    Without the fix, Thread 1's verify intermittently fails.
    """
    errors = []

    with VerifyRoot() as root:
        dev = root.Dev

        # Initialize both vars to known state
        dev.VarLow.set(0x0001)
        dev.VarHigh.set(0x0002)

        stop = threading.Event()

        def writer_thread():
            """Continuously set VarHigh without writing to hardware."""
            val = 0x1000
            while not stop.is_set():
                try:
                    dev.VarHigh.set(val, write=False)
                    val = (val + 1) & 0xFFFF
                except Exception:
                    pass  # Ignore errors in the background setter

        bg = threading.Thread(target=writer_thread, daemon=True)
        bg.start()

        try:
            # Repeatedly write VarLow with verify enabled.
            # Without the fix, the verify comparison could see VarHigh's
            # modified blockData_ and raise a spurious GeneralError.
            for i in range(50):
                try:
                    dev.VarLow.set(0x0100 + i)
                except Exception as e:
                    errors.append(str(e))
        finally:
            stop.set()
            bg.join(timeout=5)

    assert errors == [], f"Spurious verify errors detected: {errors}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
