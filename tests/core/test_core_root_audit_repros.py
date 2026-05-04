#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""Audit repros for CORE-011, CORE-012, CORE-013 in python/pyrogue/_Root.py.

CORE-011: Double assignment `self._pollQueue = self._pollQueue = pr.PollQueue(root=self)`
          at line 243 — a copy-paste artifact; the first assignment is redundant.
CORE-012: updateGroup() catches bare `except Exception` around
          `self._updateTrack[tid].increment(period)`, silently swallowing any
          non-KeyError exception raised by the existing tracker.
CORE-013: _queueUpdates() uses the same bare `except Exception` pattern,
          silently swallowing non-KeyError exceptions from an existing tracker.
"""

import pathlib
import threading

import pyrogue._Root as _root_module


def test_root_double_assignment_pollqueue_core_011():
    """Verify that the double-assignment bug in _Root.__init__ is absent.

    On HEAD, python/pyrogue/_Root.py line 243 contains:
        self._pollQueue = self._pollQueue = pr.PollQueue(root=self)
    which is a redundant double assignment. This test reads the source file
    and asserts the literal token is not present.
    """
    src_file = pathlib.Path(__file__).parent.parent.parent / 'python' / 'pyrogue' / '_Root.py'

    assert src_file.exists(), (
        "CORE-011: cannot locate python/pyrogue/_Root.py relative to test tree"
    )

    content = src_file.read_text()

    assert 'self._pollQueue = self._pollQueue =' not in content, (
        "CORE-011: double assignment to self._pollQueue present in _Root.py; "
        "line 243 contains `self._pollQueue = self._pollQueue = pr.PollQueue(root=self)`. "
        "The first assignment is a redundant copy-paste artifact."
    )


def test_root_updategroup_swallow_non_keyerror_core_012(memory_root):
    """Verify that non-KeyError exceptions in updateGroup() are propagated.

    On HEAD, python/pyrogue/_Root.py line 585-590 uses a bare
    `except Exception` around `self._updateTrack[tid].increment(period)`.
    When the tracker ALREADY EXISTS for the thread (no KeyError), but
    increment() raises RuntimeError, the bare except catches it silently
    and falls into the recovery block. Only the recovery block's second
    increment() call raises visibly. This test patches increment() to raise
    on the first call only (the second succeeds), then verifies the first
    exception propagated. On HEAD it does not — the bug is confirmed.
    """
    tid = threading.get_ident()

    # Pre-create a tracker for this thread so the first lookup succeeds
    # and increment() is called on the EXISTING tracker (not KeyError path).
    with memory_root._updateLock:
        memory_root._updateTrack[tid] = _root_module.UpdateTracker(memory_root._updateQueue)

    original_increment = _root_module.UpdateTracker.increment
    call_count = [0]

    def first_raise_then_ok(self, period):
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError('CORE-012-first-call-sentinel')
        return original_increment(self, period)

    _root_module.UpdateTracker.increment = first_raise_then_ok

    exception_propagated = False
    try:
        with memory_root.updateGroup():
            pass
    except RuntimeError as exc:
        if 'CORE-012-first-call-sentinel' in str(exc):
            exception_propagated = True
    finally:
        _root_module.UpdateTracker.increment = original_increment

    assert exception_propagated, (
        "CORE-012: bare except swallowed RuntimeError in updateGroup(); "
        "RuntimeError from the first increment() call was silently caught "
        "and discarded — only KeyError should be caught in this except clause"
    )


def test_root_queueupdates_swallow_non_keyerror_core_013(memory_root):
    """Verify that non-KeyError exceptions in _queueUpdates() are propagated.

    On HEAD, python/pyrogue/_Root.py line 1199-1204 uses the same bare
    `except Exception` pattern as updateGroup(), swallowing any non-KeyError
    exception from an existing tracker's update() call. This test patches
    update() to raise on the first call only (recovery succeeds), then
    asserts the first exception propagated. On HEAD it does not.
    """
    tid = threading.get_ident()

    # Pre-create a tracker for this thread
    with memory_root._updateLock:
        memory_root._updateTrack[tid] = _root_module.UpdateTracker(memory_root._updateQueue)

    original_update = _root_module.UpdateTracker.update
    call_count = [0]

    def first_raise_then_ok(self, var):
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError('CORE-013-first-call-sentinel')
        return original_update(self, var)

    _root_module.UpdateTracker.update = first_raise_then_ok

    exception_propagated = False
    try:
        memory_root._queueUpdates(memory_root.enable)
    except RuntimeError as exc:
        if 'CORE-013-first-call-sentinel' in str(exc):
            exception_propagated = True
    finally:
        _root_module.UpdateTracker.update = original_update

    assert exception_propagated, (
        "CORE-013: bare except swallowed RuntimeError in _queueUpdates(); "
        "RuntimeError from the first update() call was silently caught "
        "and discarded — only KeyError should be caught in this except clause"
    )
