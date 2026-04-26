#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : Block::getBytes range regression tests
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
# Pins the contract that Block::getBytes raises when an index is out of range
# for a list variable. Mirrors test_block_setbytes_range.py so reads and
# writes cannot drift apart on this contract: the dead ``index < 0`` disjunct
# was dropped from setBytes() and getBytes() in the same hardening pass, and
# both functions take ``uint32_t index``, so the only meaningful range check
# is ``index >= numValues_``.

import pyrogue as pr
import pytest
import rogue.interfaces.memory


class _ListRoot(pr.Root):
    def __init__(self) -> None:
        super().__init__(name="ListRoot", description="getBytes list test", pollEn=False)
        sim = rogue.interfaces.memory.Emulate(4, 0x1000)
        self.addInterface(sim)
        self.add(pr.Device(name="Dev", offset=0, memBase=sim))
        self.Dev.add(pr.RemoteVariable(
            name="UInt32List",
            offset=0,
            bitOffset=0,
            base=pr.UInt,
            mode="RW",
            disp="{}",
            numValues=8,
            valueBits=32,
            valueStride=32,
        ))
        self.Dev.add(pr.RemoteVariable(
            name="UInt32ListBE",
            offset=0x100,
            bitOffset=0,
            base=pr.UIntBE,        # forces byteReverse_ = True in C++ Variable
            mode="RW",
            disp="{}",
            numValues=8,
            valueBits=32,
            valueStride=32,
        ))


def test_getbytes_out_of_range_raises():
    """Out-of-range index on a list variable read must raise."""
    with _ListRoot() as root:
        var = root.Dev.UInt32List
        # Sanity: in-range read after write succeeds.
        var.set(0xDEADBEEF, index=0)
        assert var.get(index=0) == 0xDEADBEEF

        # Out-of-range read must raise. Run the call repeatedly so the
        # dropped ``index < 0`` disjunct in getBytes() can never silently
        # turn into a buffer over-read regression.
        for _ in range(64):
            with pytest.raises(Exception):
                var.get(index=999)


def test_getbytes_out_of_range_be_raises():
    """Out-of-range index on a byte-reversed list variable read must raise."""
    with _ListRoot() as root:
        var = root.Dev.UInt32ListBE
        # Sanity: in-range read after write succeeds.
        var.set(0xCAFEBABE, index=0)
        assert var.get(index=0) == 0xCAFEBABE

        for _ in range(64):
            with pytest.raises(Exception):
                var.get(index=999)


def test_getbytes_in_range_roundtrip():
    """All in-range indices on a list variable round-trip without raising."""
    with _ListRoot() as root:
        var = root.Dev.UInt32List
        for i in range(8):
            var.set(0x10000 + i, index=i)
        for i in range(8):
            assert var.get(index=i) == 0x10000 + i

        # Boundary check: numValues_ - 1 is in range, numValues_ is not.
        var.set(0x20000, index=7)
        assert var.get(index=7) == 0x20000
        with pytest.raises(Exception):
            var.get(index=8)
