#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : Block::setBytes range / byte-reverse regression tests
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
# Pins the contract that Block::setBytes raises when an index is out of range,
# including for big-endian (byteReverse_) variables that take the malloc-copy
# path. The malloc copy is what the new ``free(buff)`` guard in setBytes
# protects against leaking on the throw; the throw itself is the public
# contract this test exercises.
#
# The leak fix proper requires a leak detector (ASan / Valgrind) to observe
# directly; we still loop the offending call enough times that an unbounded
# leak would show up under any sanitizer-enabled CI run.

import pyrogue as pr
import pytest
import rogue.interfaces.memory


class _BERoot(pr.Root):
    def __init__(self) -> None:
        super().__init__(name="BERoot", description="big-endian list test", pollEn=False)
        sim = rogue.interfaces.memory.Emulate(4, 0x1000)
        self.addInterface(sim)
        self.add(pr.Device(name="Dev", offset=0, memBase=sim))
        self.Dev.add(pr.RemoteVariable(
            name="UInt32ListBE",
            offset=0,
            bitOffset=0,
            base=pr.UIntBE,        # forces byteReverse_ = True in C++ Variable
            mode="RW",
            disp="{}",
            numValues=8,
            valueBits=32,
            valueStride=32,
        ))


def test_setbytes_out_of_range_be_raises():
    """Out-of-range index on a byte-reversed list variable must raise."""
    with _BERoot() as root:
        var = root.Dev.UInt32ListBE
        # Sanity: in-range write succeeds.
        var.set(0xDEADBEEF, index=0)
        assert var.get(index=0) == 0xDEADBEEF

        # Out-of-range write must raise. Run the call repeatedly so any
        # leak in the byte-reverse malloc copy would be amplified under
        # sanitizer-enabled CI runs.
        for _ in range(64):
            with pytest.raises(Exception):
                var.set(0xCAFEBABE, index=999)


def test_setbytes_in_range_be_roundtrip():
    """Byte-reversed list variable preserves values across the malloc copy."""
    with _BERoot() as root:
        var = root.Dev.UInt32ListBE
        for i in range(8):
            var.set(0x10000 + i, index=i)
        for i in range(8):
            assert var.get(index=i) == 0x10000 + i
