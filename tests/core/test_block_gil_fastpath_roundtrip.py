#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : Block getBytes/setBytes conditional-GIL fast-path tests
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
# Pins getBytes/setBytes value equivalence after the #1262 conditional-GIL
# change. The fast path now holds the Python GIL across the in-memory body and
# only drops it when the Block mutex is actually contended. These tests prove
# that staged (write=False / read=False) values still round-trip on the scalar,
# list, and byte-reversed (malloc-copy) paths, and that the try_to_lock fallback
# branch -- taken when two threads hit the same Block -- stays correct because
# the mutex still serializes access; only the GIL handling changed.

import threading

import pyrogue as pr
import rogue.interfaces.memory


class _MixRoot(pr.Root):
    def __init__(self) -> None:
        super().__init__(name="MixRoot", description="GIL fast-path test", pollEn=False)
        sim = rogue.interfaces.memory.Emulate(4, 0x1000)
        self.addInterface(sim)
        self.add(pr.Device(name="Dev", offset=0, memBase=sim))
        self.Dev.add(pr.RemoteVariable(
            name="Scalar",
            offset=0x0,
            bitOffset=0,
            bitSize=32,
            base=pr.UInt,
            mode="RW",
        ))
        self.Dev.add(pr.RemoteVariable(
            name="List",
            offset=0x10,
            bitOffset=0,
            base=pr.UInt,
            mode="RW",
            disp="{}",
            numValues=8,
            valueBits=32,
            valueStride=32,
        ))
        self.Dev.add(pr.RemoteVariable(
            name="ListBE",
            offset=0x40,
            bitOffset=0,
            base=pr.UIntBE,        # forces byteReverse_ = True (malloc-copy path)
            mode="RW",
            disp="{}",
            numValues=8,
            valueBits=32,
            valueStride=32,
        ))


def test_fastpath_roundtrip_single_thread():
    """Staged set/get round-trips on scalar, list, and byte-reversed paths."""
    with _MixRoot() as root:
        root.Dev.Scalar.set(0xDEADBEEF, write=False)
        assert root.Dev.Scalar.get(read=False) == 0xDEADBEEF

        for i in range(8):
            root.Dev.List.set(0x1000 + i, index=i, write=False)
            root.Dev.ListBE.set(0x2000 + i, index=i, write=False)
        for i in range(8):
            assert root.Dev.List.get(index=i, read=False) == 0x1000 + i
            assert root.Dev.ListBE.get(index=i, read=False) == 0x2000 + i


def test_fastpath_roundtrip_under_contention():
    """Two threads hitting the same Block force the try_to_lock fallback branch.

    The main thread owns index 0 of the list and verifies its own writes; a
    background thread hammers indices 1-7 of the same variable. Both go through
    the same Block mutex, so the fast-path try_to_lock will fail often enough to
    exercise the GIL-drop fallback. Values must stay exact because the mutex
    still serializes access.
    """
    with _MixRoot() as root:
        var = root.Dev.List
        stop = threading.Event()
        errors = []

        def worker():
            try:
                i = 0
                while not stop.is_set():
                    idx = 1 + (i % 7)
                    var.set(i & 0xFFFFFFFF, index=idx, write=False)
                    var.get(index=idx, read=False)
                    i += 1
            except Exception as exc:  # pragma: no cover - failure path
                errors.append(exc)

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        try:
            for i in range(20000):
                var.set(i & 0xFFFFFFFF, index=0, write=False)
                assert var.get(index=0, read=False) == (i & 0xFFFFFFFF)
        finally:
            stop.set()
            t.join(timeout=5.0)

        assert not errors, f"worker raised: {errors}"
