#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""Regression tests in python/pyrogue/_Root.py.

updateGroup() catches bare `except Exception` around
          `self._updateTrack[tid].increment(period)`, silently swallowing any
          non-KeyError exception raised by the existing tracker.
_queueUpdates() uses the same bare `except Exception` pattern,
          silently swallowing non-KeyError exceptions from an existing tracker.
"""

import threading

import pyrogue._Root as _root_module


def test_root_updategroup_swallow_non_keyerror(memory_root):
    """Verify that non-KeyError exceptions in updateGroup() are propagated."""
    tid = threading.get_ident()

    # Pre-create tracker so increment() is called on the existing tracker.
    with memory_root._updateLock:
        memory_root._updateTrack[tid] = _root_module.UpdateTracker(memory_root._updateQueue)

    original_increment = _root_module.UpdateTracker.increment
    call_count = [0]

    def first_raise_then_ok(self, period):
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError('rogue-first-call-sentinel')
        return original_increment(self, period)

    _root_module.UpdateTracker.increment = first_raise_then_ok

    exception_propagated = False
    try:
        with memory_root.updateGroup():
            pass
    except RuntimeError as exc:
        if 'rogue-first-call-sentinel' in str(exc):
            exception_propagated = True
    finally:
        _root_module.UpdateTracker.increment = original_increment

    assert exception_propagated, (
        "bare except swallowed RuntimeError in updateGroup(); "
        "RuntimeError from the first increment() call was silently caught "
        "and discarded — only KeyError should be caught in this except clause"
    )


def test_root_queueupdates_swallow_non_keyerror(memory_root):
    """Verify that non-KeyError exceptions in _queueUpdates() are propagated."""
    tid = threading.get_ident()

    # Pre-create a tracker for this thread
    with memory_root._updateLock:
        memory_root._updateTrack[tid] = _root_module.UpdateTracker(memory_root._updateQueue)

    original_update = _root_module.UpdateTracker.update
    call_count = [0]

    def first_raise_then_ok(self, var):
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError('rogue-first-call-sentinel')
        return original_update(self, var)

    _root_module.UpdateTracker.update = first_raise_then_ok

    exception_propagated = False
    try:
        memory_root._queueUpdates(memory_root.enable)
    except RuntimeError as exc:
        if 'rogue-first-call-sentinel' in str(exc):
            exception_propagated = True
    finally:
        _root_module.UpdateTracker.update = original_update

    assert exception_propagated, (
        "bare except swallowed RuntimeError in _queueUpdates(); "
        "RuntimeError from the first update() call was silently caught "
        "and discarded — only KeyError should be caught in this except clause"
    )
