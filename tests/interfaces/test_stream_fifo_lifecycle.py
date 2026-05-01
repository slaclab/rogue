#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : stream::Fifo lifecycle / partial-construction regression tests
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
# Pins the contract that ``ris::Fifo::~Fifo()`` is safe across the new
# ``if (thread_ != nullptr)`` partial-construction guard added in the
# thread-safety hardening pass. The guard mirrors the pattern already
# applied to packetizer/rssi Application+Transport dtors so the
# null-thread teardown contract is consistent across the PR.
#
# Today the partial-state dtor is unreachable from Python because Fifo's
# ``thread_(new std::thread(...))`` is in the init list -- any throw
# during that allocation skips the dtor entirely. This test exists as a
# regression smoke screen for two refactors that would re-expose the
# bug: (1) moving thread_ allocation out of the init list (e.g. into a
# start()/setX() hook), or (2) replacing ``new std::thread`` with a
# fallible factory whose throw lands after the Fifo body's first
# observable side effect. Either change would route through this test.
#
# Direct attribution of any per-cycle leak still requires a leak
# detector (ASan / Valgrind); the mallinfo2 ceiling here is a coarse
# smoke screen for catastrophic regressions only.

import gc

import pytest

import rogue.interfaces.stream

pytestmark = pytest.mark.integration


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


def _cycle() -> None:
    """One create/destroy cycle: build a Fifo, then drop it.

    Each cycle exercises the Fifo ctor's ``new std::thread(...)`` and
    the matching dtor join+delete path. The dtor's new
    ``if (thread_ != nullptr)`` guard is on every cycle even though it
    is not strictly required for in-init-list construction; pinning the
    cycle here keeps a future refactor that moves the allocation out of
    the init list from silently regressing the contract.
    """
    fifo = rogue.interfaces.stream.Fifo(0, 0, False)
    del fifo


def test_fifo_create_destroy_cycle_smoke():
    """``Fifo`` create/destroy must not have catastrophic heap growth.

    The std::thread* leak fixed by ``delete thread_`` is too small
    (~100 B per cycle) to attribute reliably without a leak detector.
    The 4 MiB ceiling here is a coarse smoke screen that catches
    catastrophic regressions (e.g. a queue or buffer pool never
    released) while leaving ASan/Valgrind to chase the small leak
    directly.

    Skipped on libcs without ``mallinfo2`` (macOS, musl).
    """
    if _mallinfo2_uordblks() is None:
        pytest.skip("mallinfo2 not available on this libc")

    # Warm-up so first-cycle internal allocations do not pollute the
    # baseline (libstdc++ thread-pool one-shots, queue arenas, etc.).
    for _ in range(4):
        _cycle()
    gc.collect()

    iterations = 200
    before = _mallinfo2_uordblks()
    for _ in range(iterations):
        _cycle()
    gc.collect()
    after = _mallinfo2_uordblks()

    delta = after - before

    assert delta < 4 * 1024 * 1024, (
        f"Fifo lifecycle has catastrophic heap growth: uordblks grew "
        f"{delta} B over {iterations} create/destroy cycles"
    )


def test_fifo_repeated_destroy_via_python_drop():
    """Multiple create-then-drop cycles must each tear down cleanly.

    The dtor's new partial-construction guard ``if (thread_ != nullptr)``
    is not exercised by drop-after-success (thread_ is always non-null
    after a successful ctor). What this test pins is the wider invariant
    that the new guard does not regress the normal-path teardown: ten
    rapid drops in a row must complete without hanging the join or
    crashing the runtime, matching the established pattern at
    tests/integration/test_tcp_core_lifecycle.py.
    """
    for _ in range(10):
        fifo = rogue.interfaces.stream.Fifo(0, 0, False)
        del fifo
    gc.collect()
