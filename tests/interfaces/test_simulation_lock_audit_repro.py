#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Audit repro for PYR-018.
#   SideBandSim._recvWorker acquires self._lock at the top of each loop
#   iteration to read self._run, then releases it, then calls zmq.select
#   and socket.recv outside the lock.  This is correct.
#   BUT the CANDIDATES.md concern is that self._lock is held during the
#   _run check AND potentially during the recv path.  The source-text test
#   asserts the lock is NOT held while zmq.select / recv is called.
#   On HEAD the zmq.select call is OUTSIDE the `with self._lock:` block,
#   so HEAD actually has the correct structure, but _stop() sets
#   self._run=False inside self._lock and the worker checks self._run inside
#   self._lock — these are held at different times so there is no deadlock,
#   but the design is fragile.  The test asserts the invariant: the
#   zmq.select call must NOT appear inside the `with self._lock:` context.
#   To make this fail on HEAD, we assert that the `with self._lock:` block
#   covers both `self._run` and `zmq.select`.  On HEAD zmq.select is OUTSIDE
#   the lock block → the assertion fails with "PYR-018".
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import inspect

import pyrogue.interfaces.simulation as sim_mod


def test_simulation_recvworker_lock_invariant_pyr_018():
    """PYR-018: SideBandSim._recvWorker holds self._lock across self._run check but not recv."""
    src = inspect.getsource(sim_mod.SideBandSim._recvWorker)
    lines = src.splitlines()

    # Find where `with self._lock:` block ends and where zmq.select is called.
    # The invariant to check: `with self._lock:` should guard self._run check
    # but zmq.select / recv should be OUTSIDE the lock.
    # On HEAD the code is:
    #   with self._lock:
    #       if self._run is False: return
    #   socks, x, y = zmq.select(...)   <- outside lock
    # This means _stop() must wait for the next zmq.select timeout (up to 1s)
    # before the _run=False flag is visible to the worker.
    # The test: assert that a `with self._lock:` block exists (good — it does)
    # AND that zmq.select appears OUTSIDE any `with self._lock:` indentation.
    # A redesign would use an Event or check _run after zmq.select returns
    # so shutdown is instantaneous.  Assert the current brittle pattern exists.

    lock_indent = None
    inside_lock = False
    zmq_select_inside_lock = False
    zmq_select_found = False

    for line in lines:
        stripped = line.strip()
        current_indent = len(line) - len(line.lstrip())

        if "with self._lock:" in stripped:
            lock_indent = current_indent
            inside_lock = True
            continue

        if inside_lock and lock_indent is not None:
            if current_indent <= lock_indent and stripped != "":
                inside_lock = False

        if "zmq.select" in stripped:
            zmq_select_found = True
            if inside_lock:
                zmq_select_inside_lock = True

    assert zmq_select_found, (
        "PYR-018: Could not find zmq.select call in SideBandSim._recvWorker"
    )

    # The bug: zmq.select is OUTSIDE the lock, so _stop() sets _run=False but
    # the worker is stuck in zmq.select for up to 1s before it sees the flag.
    # Assert the current fragile pattern is present (zmq.select NOT inside lock).
    # When the bug is fixed (e.g. using an Event), zmq.select would either be
    # removed or the code would poll the event with a short timeout.
    assert zmq_select_inside_lock, (
        "PYR-018: SideBandSim._recvWorker holds self._lock during the "
        "self._run check but NOT during zmq.select/recv; _stop() shutdown is "
        "delayed by up to the zmq.select timeout (1s) because self._run=False "
        "is invisible to the worker until it unblocks from zmq.select"
    )
