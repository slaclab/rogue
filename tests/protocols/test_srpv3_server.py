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

import pyrogue as pr
import rogue.protocols.srp
import pytest


class SrpV3TestDevice(pr.Device):
    """Device with registers for testing SrpV3 protocol round-trips."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.add(pr.RemoteVariable(
            name='ScratchPad',
            offset=0x0000,
            bitSize=32,
            mode='RW',
            base=pr.UInt,
        ))

        self.add(pr.RemoteVariable(
            name='Register1',
            offset=0x0004,
            bitSize=32,
            mode='RW',
            base=pr.UInt,
        ))

        self.add(pr.RemoteVariable(
            name='Register2',
            offset=0x0008,
            bitSize=32,
            mode='RW',
            base=pr.UInt,
        ))

        self.add(pr.RemoteVariable(
            name='WideRegister',
            offset=0x0010,
            bitSize=64,
            mode='RW',
            base=pr.UInt,
        ))


class SrpV3TestRoot(pr.Root):
    """Root that wires SrpV3 client to SrpV3Server for software-only testing."""

    def __init__(self, **kwargs):
        super().__init__(
            name='SrpV3TestRoot',
            description='SrpV3 loopback test',
            timeout=2.0,
            pollEn=False,
            **kwargs,
        )

        # SRPv3 client (master) side
        self.srp = rogue.protocols.srp.SrpV3()

        # SRPv3 server (emulated hardware endpoint)
        self.srpServer = rogue.protocols.srp.SrpV3Server()

        # Bidirectional stream connection: client <-> server
        self.srp == self.srpServer

        # Attach device to the SRPv3 memory interface
        self.add(SrpV3TestDevice(
            name='Dev',
            offset=0x00000000,
            memBase=self.srp,
        ))


class SrpV3MultiDeviceRoot(pr.Root):
    """Root with multiple devices at different offsets."""

    def __init__(self, **kwargs):
        super().__init__(
            name='SrpV3MultiRoot',
            description='SrpV3 multi-device test',
            timeout=2.0,
            pollEn=False,
            **kwargs,
        )

        self.srp = rogue.protocols.srp.SrpV3()
        self.srpServer = rogue.protocols.srp.SrpV3Server()
        self.srp == self.srpServer

        for i in range(4):
            self.add(SrpV3TestDevice(
                name=f'Dev[{i}]',
                offset=i * 0x10000,
                memBase=self.srp,
            ))


def test_srpv3_server_basic_write_read():
    """Test basic write and read-back through SrpV3 <-> SrpV3Server."""
    with SrpV3TestRoot() as root:
        root.Dev.ScratchPad.set(0xDEADBEEF)
        val = root.Dev.ScratchPad.get()
        assert val == 0xDEADBEEF


def test_srpv3_server_multiple_registers():
    """Test writing and reading multiple registers."""
    with SrpV3TestRoot() as root:
        root.Dev.ScratchPad.set(0x12345678)
        root.Dev.Register1.set(0xAABBCCDD)
        root.Dev.Register2.set(0x11223344)

        assert root.Dev.ScratchPad.get() == 0x12345678
        assert root.Dev.Register1.get() == 0xAABBCCDD
        assert root.Dev.Register2.get() == 0x11223344


def test_srpv3_server_overwrite():
    """Test that overwriting a register works correctly."""
    with SrpV3TestRoot() as root:
        root.Dev.ScratchPad.set(0x11111111)
        assert root.Dev.ScratchPad.get() == 0x11111111

        root.Dev.ScratchPad.set(0x22222222)
        assert root.Dev.ScratchPad.get() == 0x22222222


def test_srpv3_server_wide_register():
    """Test 64-bit register write and read."""
    with SrpV3TestRoot() as root:
        root.Dev.WideRegister.set(0x0102030405060708)
        val = root.Dev.WideRegister.get()
        assert val == 0x0102030405060708


def test_srpv3_server_uninitialized_read():
    """Test that reading uninitialized memory returns zero."""
    with SrpV3TestRoot() as root:
        val = root.Dev.ScratchPad.get()
        assert val == 0


def test_srpv3_server_multi_device():
    """Test multiple devices at different address offsets."""
    with SrpV3MultiDeviceRoot() as root:
        # Write different values to each device
        for i in range(4):
            root.Dev[i].ScratchPad.set(0x1000 + i)
            root.Dev[i].Register1.set(0x2000 + i)

        # Read back and verify isolation
        for i in range(4):
            assert root.Dev[i].ScratchPad.get() == 0x1000 + i
            assert root.Dev[i].Register1.get() == 0x2000 + i


def test_srpv3_server_zero_write():
    """Test writing zero to a register."""
    with SrpV3TestRoot() as root:
        root.Dev.ScratchPad.set(0xFFFFFFFF)
        assert root.Dev.ScratchPad.get() == 0xFFFFFFFF

        root.Dev.ScratchPad.set(0x00000000)
        assert root.Dev.ScratchPad.get() == 0x00000000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
