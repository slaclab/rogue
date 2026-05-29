#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import time

import pyrogue as pr
from conftest import MemoryRoot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _noop_fn(root=None, dev=None, cmd=None, arg=None):
    """No-op command function for construction tests."""
    return None


def _slow_fn():
    """Sleep briefly and return a fixed value."""
    time.sleep(0.3)
    return 'done'


# ---------------------------------------------------------------------------
# Device / Root definitions
# ---------------------------------------------------------------------------

class _SimpleDevice(pr.Device):
    """Device with a plain LocalCommand and a RemoteCommand."""

    def __init__(self, mem_base=None, **kwargs):
        kw = {}
        if mem_base is not None:
            kw['memBase'] = mem_base
        super().__init__(**kw, **kwargs)

        self.add(pr.LocalCommand(
            name='Local',
            function=_slow_fn,
            retValue='',
            description='LocalCommand for blocking/non-blocking tests.',
        ))

        if mem_base is not None:
            self.add(pr.RemoteCommand(
                name='Remote',
                offset=0x00,
                bitSize=8,
                base=pr.UInt,
                value=0,
                function=_noop_fn,
                description='RemoteCommand for construction tests.',
            ))


class _SimpleRoot(pr.Root):
    def __init__(self):
        super().__init__(name='SimpleRoot', pollEn=False)
        self.add(_SimpleDevice(name='Dev'))


class _RemoteRoot(MemoryRoot):
    def __init__(self):
        super().__init__(name='RemoteRoot')
        self.add(_SimpleDevice(name='Dev', mem_base=self._mem))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_no_sibling_variables_created():
    """Commands must NOT inject any sibling status variables into the tree.
    The running/result/error status is exposed via properties on the Command."""
    with _SimpleRoot() as root:
        dev = root.Dev
        assert 'LocalRunning' not in dev.nodes
        assert 'LocalResult' not in dev.nodes
        assert 'LocalError' not in dev.nodes


def test_blocking_true_returns_synchronously():
    """Default call (blocking=True) executes synchronously and returns the
    function's return value."""
    with _SimpleRoot() as root:
        result = root.Dev.Local()
        assert result == 'done'


def test_blocking_false_returns_immediately():
    """call(blocking=False) dispatches a worker thread and returns None
    immediately, well before the function completes."""
    with _SimpleRoot() as root:
        cmd = root.Dev.Local
        t0 = time.monotonic()
        result = cmd(blocking=False)
        elapsed = time.monotonic() - t0

        assert result is None
        assert elapsed < 0.2, f"blocking=False should return immediately, took {elapsed:.2f}s"

        # Wait for the worker to complete.
        deadline = time.monotonic() + 5.0
        while cmd.running and time.monotonic() < deadline:
            time.sleep(0.05)

        assert not cmd.running
        assert cmd.result == 'done'
        assert cmd.error == ''


def test_running_property_tracks_worker():
    """The `running` property is True while the worker is alive."""
    with _SimpleRoot() as root:
        cmd = root.Dev.Local

        assert not cmd.running

        cmd(blocking=False)
        # Give the thread a moment to start.
        time.sleep(0.05)
        assert cmd.running

        # Wait for completion.
        deadline = time.monotonic() + 5.0
        while cmd.running and time.monotonic() < deadline:
            time.sleep(0.05)

        assert not cmd.running


def test_error_property_captures_exception():
    """When the worker function raises, `error` captures str(exc) and
    `result` is unchanged."""
    def _boom():
        raise RuntimeError("test error")

    with _SimpleRoot() as root:
        cmd = root.Dev.Local
        cmd.replaceFunction(_boom)

        result_before = cmd.result

        cmd(blocking=False)
        deadline = time.monotonic() + 5.0
        while cmd.running and time.monotonic() < deadline:
            time.sleep(0.05)

        assert not cmd.running
        assert cmd.error == 'test error'
        assert cmd.result == result_before


def test_remote_command_constructs_without_nonblocking():
    """RemoteCommand no longer accepts a nonBlocking parameter and
    constructs cleanly without it."""
    with _RemoteRoot() as root:
        dev = root.Dev
        assert 'Remote' in dev.nodes
        assert not dev.Remote.running
