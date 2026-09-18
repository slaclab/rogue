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
# Pins the contract that a process holding a ``VirtualClient`` exits on its
# own, without the caller having to call ``stop()``.
#
# ``_monWorker`` loops on ``while self._monEnable: time.sleep(1)``. When the
# monitor thread was created without ``daemon=True``, nothing was left to
# clear ``_monEnable`` once the main thread finished, so CPython blocked
# forever in ``threading._shutdown()`` joining it. Any script that built a
# client and fell off the end hung at exit (issue #1294, originally #1238;
# the fix in PR #1239 was reverted by PR #1252 and the regression shipped in
# v6.15.0).
#
# Two changes are required and this module covers both, because each alone
# is insufficient:
#
#   * ``daemon=True`` on ``_monThread`` -- removes the guaranteed hang, but
#     on its own leaves an intermittent ``SIGABRT`` at exit: quiescing the
#     Python loop while the C++ ``ZmqClient`` is still live can unwind
#     ``pthread_exit`` through C++ frames.
#   * a ``threading._register_atexit`` hook running the full ``stop()`` --
#     tears the native client down before the interpreter joins threads.
#     ``atexit`` is too late by construction: ``threading._shutdown()`` runs
#     its joins first, so an ``atexit`` hook is queued behind the very join
#     it would release.
#
# Dropping either change makes ``test_client_process_exits_without_explicit_stop``
# fail -- as a timeout without the daemon flag, or as a nonzero signal exit
# without the hook.

import os
import subprocess
import sys

import pytest

import pyrogue
import pyrogue.interfaces

pytestmark = pytest.mark.integration


# Connects, confirms the link, then falls off the end of the module without
# calling stop() -- deliberately the "does nothing unusual" client from the
# issue report. Run with ``python -c``, so sys.argv[1] is the port.
_CLIENT_SNIPPET = """
import sys
from pyrogue.interfaces import VirtualClient

client = VirtualClient('127.0.0.1', int(sys.argv[1]))
assert client.linked, 'client did not link to the test server'
"""

# Generous relative to a clean exit (well under a second) so this does not
# flake on a loaded CI host, while still bounded well below the pytest job.
_EXIT_TIMEOUT_S = 30

# The abort this guards against was measured at roughly 1 run in 10, so a
# single trial would miss it more often than not.
_EXIT_TRIALS = 5


def _clear_virtual_client_cache() -> None:
    for client in list(pyrogue.interfaces.VirtualClient.ClientCache.values()):
        try:
            client.stop()
            client._stop()
        except Exception:
            pass
    pyrogue.interfaces.VirtualClient.ClientCache.clear()


class _ExitRoot(pyrogue.Root):
    def __init__(self, *, name: str, port: int):
        super().__init__(name=name, pollEn=False)
        self.add(pyrogue.LocalVariable(name='Value', value=0, mode='RO'))
        self.zmqServer = pyrogue.interfaces.ZmqServer(root=self, addr='127.0.0.1', port=port)
        self.addInterface(self.zmqServer)


def test_client_process_exits_without_explicit_stop(free_zmq_port):
    """A client process must exit without an explicit ``stop()`` call.

    Runs the client in a subprocess because the behavior under test *is*
    interpreter shutdown: it cannot be observed from inside a pytest process
    that has to stay alive. Pre-fix this times out; with ``daemon=True`` but
    no teardown hook it exits on a signal (``-6`` / ``SIGABRT``) some of the
    time, so the exit code is asserted to be exactly 0 on every trial.
    """
    port = free_zmq_port
    _clear_virtual_client_cache()

    with _ExitRoot(name='ExitRoot', port=port):
        for trial in range(_EXIT_TRIALS):
            try:
                completed = subprocess.run(
                    [sys.executable, '-c', _CLIENT_SNIPPET, str(port)],
                    timeout=_EXIT_TIMEOUT_S,
                    capture_output=True,
                    text=True,
                    env=os.environ.copy(),
                )
            except subprocess.TimeoutExpired:
                pytest.fail(
                    f"trial {trial}: client process did not exit within "
                    f"{_EXIT_TIMEOUT_S}s. The monitor thread is keeping the "
                    f"interpreter alive: threading._shutdown() is joining "
                    f"_monWorker, which loops until _monEnable is cleared. "
                    f"_monThread needs daemon=True."
                )

            assert completed.returncode == 0, (
                f"trial {trial}: client process exited with "
                f"{completed.returncode} (negative means a signal; -6 is "
                f"SIGABRT from pthread_exit unwinding through C++ frames). "
                f"The shutdown hook must run the full stop() so the C++ "
                f"ZmqClient is torn down before the interpreter finalizes.\n"
                f"stderr:\n{completed.stderr}"
            )

    _clear_virtual_client_cache()


def test_monitor_thread_is_daemon(free_zmq_port):
    """``_monThread`` must be a daemon thread.

    Pins the flag directly so a revert is reported as an obvious one-line
    regression rather than only as a subprocess timeout.
    """
    port = free_zmq_port
    _clear_virtual_client_cache()

    with _ExitRoot(name='DaemonRoot', port=port):
        client = pyrogue.interfaces.VirtualClient(addr='127.0.0.1', port=port)
        try:
            assert client._monThread is not None
            assert client._monThread.daemon is True, (
                "VirtualClient._monThread is not a daemon thread; "
                "threading._shutdown() will block joining _monWorker and any "
                "process holding this client will hang at exit."
            )
        finally:
            client.stop()

    _clear_virtual_client_cache()


def test_shutdown_hook_stops_cached_clients(free_zmq_port):
    """The registered hook must stop clients still live in ``ClientCache``.

    Invokes the hook body directly rather than waiting on interpreter
    teardown, so the sweep is pinned deterministically; the subprocess test
    above covers that it is actually wired into shutdown. ``stop()`` drops its
    own cache entry, so an emptied cache is the observable effect.

    Imported inside the test on purpose: at module scope, a tree without the
    fix fails collection and takes the two behavioral tests down with it,
    hiding the hang this module exists to report.
    """
    from pyrogue.interfaces._Virtual import _stopCachedClients

    port = free_zmq_port
    _clear_virtual_client_cache()

    with _ExitRoot(name='HookRoot', port=port):
        client = pyrogue.interfaces.VirtualClient(addr='127.0.0.1', port=port)
        assert client.root is not None
        assert pyrogue.interfaces.VirtualClient.ClientCache, (
            "client construction did not populate ClientCache; this test is "
            "not measuring what it claims to."
        )

        _stopCachedClients()

        assert not pyrogue.interfaces.VirtualClient.ClientCache, (
            "shutdown hook left clients in ClientCache; stop() was not "
            "called on the cached client."
        )
        assert client._vcInitialized is False, (
            "shutdown hook did not run the full stop(): _vcInitialized is "
            "still set, so the C++ ZmqClient teardown did not happen."
        )

        # The hook runs once per process but callers may also have stopped
        # their clients already; a second sweep must stay harmless.
        _stopCachedClients()

    _clear_virtual_client_cache()
