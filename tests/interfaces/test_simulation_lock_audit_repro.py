#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Regression test.
#   SideBandSim._recvWorker must NOT hold self._lock while blocking inside
#   zmq.select(); _stop() needs the same lock to set self._run=False, so
#   shutdown would otherwise stall behind the select timeout.
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


def test_simulation_recvworker_lock_invariant():
    """SideBandSim._recvWorker must release self._lock before zmq.select."""
    src = inspect.getsource(sim_mod.SideBandSim._recvWorker)
    lines = src.splitlines()

    # Walk the function body and track indentation of any active `with
    # self._lock:` block.  zmq.select must appear OUTSIDE the lock block
    # so _stop() (which sets self._run=False under the same lock) is not
    # blocked behind the select timeout.

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
        "Could not find zmq.select call in SideBandSim._recvWorker"
    )

    assert not zmq_select_inside_lock, (
        "SideBandSim._recvWorker holds self._lock while blocked in "
        "zmq.select; _stop() needs the same lock to set self._run=False, so "
        "shutdown stalls behind the select timeout. Release the lock after "
        "the self._run check and call zmq.select unlocked."
    )
