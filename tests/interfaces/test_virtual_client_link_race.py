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
#
# Regression tests for VirtualClient link-state race conditions.
#
# The monitor thread (_monWorker) calls _checkLinkState() every ~1 s while
# request threads call _requestDone() and the SUB socket calls _doUpdate().
# Without proper locking, _link and _ltime can be read in a torn state,
# causing spurious link-down/link-up oscillations.
#
# Rather than trying to trigger the race via timing, these tests assert
# the invariant directly: each test patches time.time() (or installs a
# tracking lock) to record whether _reqLock was held at the moment the
# shared state is read or written.  A violation shows up as a locked=False
# observation, regardless of scheduler behavior.

import importlib.util
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.integration


def _load_virtual_client():
    module_path = (
        Path(__file__).resolve().parents[2]
        / "python" / "pyrogue" / "interfaces" / "_Virtual.py"
    )
    spec = importlib.util.spec_from_file_location(
        "rogue_test_virtual_module", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.VirtualClient, module


VirtualClient, _virtual_mod = _load_virtual_client()


class _LogRecorder:
    def __init__(self):
        self.messages = []

    def warning(self, message):
        self.messages.append(message)


def _make_client(link_timeout=10.0, request_stall_timeout=None):
    client = VirtualClient.__new__(VirtualClient, "localhost", 9099)
    client._monitors = []
    client._root = SimpleNamespace(name="root")
    client._log = _LogRecorder()
    client._reqLock = threading.Lock()
    client._reqCount = 0
    client._reqSince = None
    client._ltime = time.time()
    client._link = True
    client._linkTimeout = link_timeout
    client._requestStallTimeout = request_stall_timeout
    client._monEnable = False
    client._monThread = None
    return client


def test_ltime_written_under_lock():
    """_requestDone must write _ltime inside _reqLock.

    On unpatched code, _ltime is written OUTSIDE the lock, so a
    concurrent _checkLinkState() can read stale _ltime between the
    lock release and the assignment.  This test verifies the write
    occurs while the lock is held.

    Strategy: override _requestDone to record whether _reqLock is held
    at the moment _ltime is assigned.  On unpatched code, it will not
    be held.
    """
    client = _make_client()
    lock_held_during_ltime_write = []

    original_requestDone = VirtualClient._requestDone

    def instrumented_requestDone(self, success):
        original_time = time.time

        def tracking_time():
            # When time.time() is called for _ltime assignment,
            # check if the lock is held
            locked = self._reqLock.locked()
            lock_held_during_ltime_write.append(locked)
            return original_time()

        with patch.object(_virtual_mod.time, 'time', side_effect=tracking_time):
            original_requestDone(self, success)

    with patch.object(VirtualClient, '_requestDone', instrumented_requestDone):
        client._link = False
        client._requestDone(True)

    assert len(lock_held_during_ltime_write) > 0, (
        "_requestDone did not call time.time() — test is broken"
    )
    # _requestDone only calls time.time() once, to assign _ltime on a
    # successful reply (_reqSince is managed by _requestStart). On
    # unpatched code that assignment happened outside the lock; after
    # the fix it must happen while _reqLock is held.
    ltime_call_locked = lock_held_during_ltime_write[-1]
    assert ltime_call_locked, (
        "_ltime was written outside _reqLock — race condition present. "
        f"Lock states per time.time() call: {lock_held_during_ltime_write}"
    )


def test_checkLinkState_reads_under_lock():
    """_checkLinkState must read _ltime and _link under _reqLock.

    On unpatched code, _checkLinkState reads _ltime and _link without
    any lock, allowing torn reads from concurrent _requestDone writes.

    Strategy: replace _reqLock with an instrumented wrapper that records
    whether _checkLinkState ever acquires it.
    """
    client = _make_client(link_timeout=10.0)
    client._ltime = time.time()

    class TrackingLock:
        def __init__(self):
            self._lock = threading.Lock()
            self.acquired_count = 0

        def acquire(self, *args, **kwargs):
            result = self._lock.acquire(*args, **kwargs)
            self.acquired_count += 1
            return result

        def release(self):
            self._lock.release()

        def locked(self):
            return self._lock.locked()

        def __enter__(self):
            self.acquire()
            return self

        def __exit__(self, *args):
            self.release()

    tracker = TrackingLock()
    client._reqLock = tracker

    client._checkLinkState()

    assert tracker.acquired_count > 0, (
        "_checkLinkState did not acquire _reqLock — "
        "_ltime/_link reads are unprotected (race condition present)"
    )


def test_doUpdate_writes_ltime_under_lock():
    """_doUpdate must write _ltime under _reqLock.

    On unpatched code, _doUpdate writes _ltime without any lock.
    """
    client = _make_client()
    client._varListeners = []
    client._root = None

    lock_held = []
    original_time = time.time

    def tracking_time():
        locked = client._reqLock.locked()
        lock_held.append(locked)
        return original_time()

    with patch.object(_virtual_mod.time, 'time', side_effect=tracking_time):
        client._doUpdate(b'\x80\x03}q\x00.')  # pickle.dumps({})

    assert len(lock_held) > 0, (
        "_doUpdate did not call time.time() — test is broken"
    )
    assert lock_held[0], (
        "_doUpdate wrote _ltime outside _reqLock — race condition present. "
        f"Lock states: {lock_held}"
    )


def test_stop_joins_monitor_thread():
    """stop() must join the monitor thread, not just set the flag.

    On unpatched code, stop() only sets _monEnable = False but does not
    wait for the thread to exit, allowing the thread to outlive the client.
    """
    client = _make_client()
    client._monEnable = True
    client._monThread = threading.Thread(
        target=client._monWorker, daemon=True)
    client._monThread.start()

    time.sleep(0.1)
    assert client._monThread.is_alive()

    client.stop()

    # Give a short grace period — if stop() joined, thread is already dead.
    # If stop() only set the flag, thread sleeps for up to 1s before checking.
    time.sleep(0.05)

    assert not client._monThread.is_alive(), (
        "Monitor thread still alive 50ms after stop() — "
        "stop() did not join the thread (only set the flag)"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
