#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import threading
import time

import pytest
import pyrogue as pr
import pyrogue.interfaces as pr_interfaces


pytestmark = pytest.mark.integration


# TEST-04 uses _LogRecorder to capture server-side log warnings from the live command.
class _LogRecorder:
    """Minimal logger stub that records warning() calls for TEST-04 assertions."""

    def __init__(self):
        self.messages = []

    def warning(self, message):
        self.messages.append(message)

    def __getattr__(self, name):
        # Absorb any other logger surface (debug/info/error/critical/exception)
        # without raising AttributeError.  Keeps TEST-04 robust against future
        # implementation changes that might add new self._log calls inside the
        # non-blocking dispatch path.
        return lambda *a, **k: None


def raise_boom():
    """Module-level raising function — keeps the traceback readable for TEST-06."""
    raise RuntimeError("boom")


def _async_sleep_fn():
    """Sleep 2 seconds and return a fixed string result."""
    time.sleep(2.0)
    return 'done'


class ZmqIntegrationDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # TEST-01 (#1243): synchronous long-running command; blocks the client for the
        # full function duration regardless of linkTimeout.  A 3-second sleep stands in
        # for the issue #1243 blocking pattern within the CI time budget.
        self.add(pr.LocalCommand(
            name='SyncSleep',
            description='Synchronous sleep — blocks caller for full duration.',
            function=lambda: time.sleep(3),
        ))

        # TEST-02: same pattern with nonBlocking=True; call returns immediately and
        # the client polls the auto-added Running/Result/Error sibling variables.
        self.add(pr.LocalCommand(
            name='AsyncSleep',
            description='Non-blocking sleep — returns immediately; poll AsyncSleepRunning.',
            function=_async_sleep_fn,
            nonBlocking=True,
            retValue='',
        ))

        # Sync regression: default-construction command must still return its
        # function value synchronously after the nonBlocking feature is introduced.
        self.add(pr.LocalCommand(
            name='SyncMul',
            description='Synchronous multiply — returns arg * 3.',
            value=0,
            retValue=0,
            function=lambda arg: arg * 3,
        ))

        # TEST-04: 2-second sleep — used for re-entry rejection test.
        self.add(pr.LocalCommand(
            name='AsyncSlow',
            description='Non-blocking 2-second sleep — re-entry rejection test.',
            function=lambda: time.sleep(2.0),
            nonBlocking=True,
            retValue='',
        ))

        # TEST-05: 5-second sleep — used for Root.stop() clean-join test.
        self.add(pr.LocalCommand(
            name='AsyncLong',
            description='Non-blocking 5-second sleep — shutdown join test.',
            function=lambda: time.sleep(5.0),
            nonBlocking=True,
            retValue='',
        ))

        # TEST-06: raises RuntimeError — used for worker error-path test.
        self.add(pr.LocalCommand(
            name='AsyncBoom',
            description='Non-blocking command that raises — error-path test.',
            function=raise_boom,
            nonBlocking=True,
        ))


class ZmqIntegrationRoot(pr.Root):
    def __init__(self, *, port):
        super().__init__(name='Top', pollEn=False)
        self.add(ZmqIntegrationDevice(name='Dev'))

        self.zmqServer = pr_interfaces.ZmqServer(root=self, addr='*', port=port)
        self.addInterface(self.zmqServer)


def test_sync_command_baseline_blocks_link(free_zmq_port):
    # TEST-01 (#1243): a synchronous LocalCommand over ZMQ blocks the client thread
    # for the entire duration of the server-side function.  The VirtualClient does NOT
    # raise after linkTimeout when a request is in flight (the idle-timeout check is
    # suppressed while reqPending=True).  This test asserts the blocking behaviour so
    # that the contrast with TEST-02 (nonBlocking=True) is explicit.
    pr_interfaces.VirtualClient.ClientCache.clear()

    with ZmqIntegrationRoot(port=free_zmq_port) as root:
        client = pr_interfaces.VirtualClient(
            addr='127.0.0.1',
            port=root.zmqServer.port(),
            linkTimeout=2.0,
        )
        try:
            remote_dev = client.root.Dev
            t0 = time.monotonic()
            remote_dev.SyncSleep()
            elapsed = time.monotonic() - t0
            # The synchronous call must block for the full 3-second sleep.
            # TEST-01 assertion shape: wall-clock >= sleep_duration - 0.5 s.
            assert elapsed >= 2.5, (
                f"Sync command should block for ~3 s but returned in {elapsed:.2f} s"
            )
        finally:
            client.stop()
            pr_interfaces.VirtualClient.ClientCache.clear()


def test_nonblocking_command_returns_immediately(wait_until, free_zmq_port):
    # TEST-02: with nonBlocking=True the command call returns immediately (well under
    # linkTimeout=2.0).  The auto-added AsyncSleepRunning / AsyncSleepResult /
    # AsyncSleepError sibling LocalVariables are polled via the VirtualClient until
    # the worker completes naturally.
    pr_interfaces.VirtualClient.ClientCache.clear()

    with ZmqIntegrationRoot(port=free_zmq_port) as root:
        client = pr_interfaces.VirtualClient(
            addr='127.0.0.1',
            port=root.zmqServer.port(),
            linkTimeout=2.0,
        )
        try:
            remote_dev = client.root.Dev

            t0 = time.monotonic()
            remote_dev.AsyncSleep()
            elapsed = time.monotonic() - t0

            # (a) Call must return immediately — well under linkTimeout.
            assert elapsed < 1.0, (
                f"nonBlocking call should return immediately but took {elapsed:.2f} s"
            )

            # (b) Running flips to True while the worker is in flight.
            assert wait_until(
                lambda: remote_dev.AsyncSleepRunning.get() is True,
                timeout=5.0,
            ), "AsyncSleepRunning never became True"

            # (c) Running flips to False once the 2-second worker completes.
            assert wait_until(
                lambda: remote_dev.AsyncSleepRunning.get() is False,
                timeout=10.0,
            ), "AsyncSleepRunning never returned to False"

            # (d) Result carries the function's return value.
            assert remote_dev.AsyncSleepResult.get() == 'done', (
                f"Expected AsyncSleepResult='done', got {remote_dev.AsyncSleepResult.get()!r}"
            )

            # (e) Error is empty on a successful run.
            assert remote_dev.AsyncSleepError.get() == '', (
                f"Expected empty AsyncSleepError, got {remote_dev.AsyncSleepError.get()!r}"
            )
        finally:
            client.stop()
            pr_interfaces.VirtualClient.ClientCache.clear()


def test_sync_command_returns_value(free_zmq_port):
    # Sync regression: default-construction LocalCommand (nonBlocking=False) must
    # continue to return the function's value synchronously over VirtualClient.
    # Pins the "default-False keeps every existing example unchanged" promise.
    pr_interfaces.VirtualClient.ClientCache.clear()

    with ZmqIntegrationRoot(port=free_zmq_port) as root:
        client = pr_interfaces.VirtualClient(
            addr='127.0.0.1',
            port=root.zmqServer.port(),
            linkTimeout=2.0,
        )
        try:
            remote_dev = client.root.Dev
            result = remote_dev.SyncMul(4)
            assert result == 12, f"Expected SyncMul(4)==12, got {result!r}"
        finally:
            client.stop()
            pr_interfaces.VirtualClient.ClientCache.clear()


def test_reentrant_call_is_rejected_and_logged(wait_until, free_zmq_port):
    # TEST-04 (#1243): a second call to a non-blocking Command while it is running
    # is logged as "Command already running!" and silently rejected — no parallel
    # worker is spawned and Result is not modified.
    pr_interfaces.VirtualClient.ClientCache.clear()

    with ZmqIntegrationRoot(port=free_zmq_port) as root:
        client = pr_interfaces.VirtualClient(
            addr='127.0.0.1',
            port=root.zmqServer.port(),
            linkTimeout=5.0,
        )
        cmd = root.Dev.AsyncSlow
        original_log = cmd._log
        recorder = _LogRecorder()
        cmd._log = recorder
        try:
            remote_dev = client.root.Dev

            # Snapshot Result before the first call — unchanged-sentinel for (c).
            result_before = remote_dev.AsyncSlowResult.get()

            # First call — worker spawns and begins its 2-second sleep.
            remote_dev.AsyncSlow()

            # Wait for Running to flip True before issuing the re-entry call.
            assert wait_until(
                lambda: remote_dev.AsyncSlowRunning.get() is True,
                timeout=5.0,
            ), "AsyncSlowRunning never became True after first call"

            # Second call while the worker is in flight — must be silently rejected.
            result = remote_dev.AsyncSlow()
            assert result is None, (
                f"Re-entry call should return None, got {result!r}"
            )

            # (a) Exactly one warning logged on the server side.
            assert recorder.messages == ["Command already running!"], (
                f"Expected ['Command already running!'] but got {recorder.messages!r}"
            )

            # (b) Only one worker thread alive for this command path.
            worker_threads = [
                t for t in threading.enumerate()
                if t.name == f'{cmd.path}.worker'
            ]
            assert len(worker_threads) == 1, (
                f"Expected 1 worker thread, found {len(worker_threads)}"
            )

            # (c) Result is unchanged — re-entry rejection did not modify it.
            assert remote_dev.AsyncSlowResult.get() == result_before, (
                f"Result changed after re-entry rejection: "
                f"before={result_before!r}, after={remote_dev.AsyncSlowResult.get()!r}"
            )

            # Wait for the first worker to finish naturally before cleanup.
            assert wait_until(
                lambda: remote_dev.AsyncSlowRunning.get() is False,
                timeout=10.0,
            ), "AsyncSlowRunning never returned to False after worker completion"

        finally:
            cmd._log = original_log
            client.stop()
            pr_interfaces.VirtualClient.ClientCache.clear()


def test_root_stop_joins_in_flight_worker(wait_until, free_zmq_port):
    # TEST-05 (#1243): Root.stop() (via ZmqIntegrationRoot context exit) joins
    # any in-flight non-blocking Command worker indefinitely — no .worker thread
    # survives shutdown.  Workers are daemon=False and Root.stop() joins them
    # without a timeout.
    pr_interfaces.VirtualClient.ClientCache.clear()

    with ZmqIntegrationRoot(port=free_zmq_port) as root:
        client = pr_interfaces.VirtualClient(
            addr='127.0.0.1',
            port=root.zmqServer.port(),
            linkTimeout=10.0,
        )
        try:
            remote_dev = client.root.Dev

            # Start the 5-second worker.
            remote_dev.AsyncLong()

            # Confirm the worker is in flight before triggering shutdown.
            assert wait_until(
                lambda: remote_dev.AsyncLongRunning.get() is True,
                timeout=5.0,
            ), "AsyncLongRunning never became True"

        finally:
            client.stop()
            pr_interfaces.VirtualClient.ClientCache.clear()

    # with block exit: root.stop() is called, which joins the in-flight worker
    # indefinitely.  The 5-second sleep must complete before this line is reached.
    # Scope the leak check to threads this feature owns (".worker") to avoid
    # false positives from unrelated background threads (pytest, ZMQ, logging).
    post_threads = {t.name for t in threading.enumerate()}
    leaked_workers = [name for name in post_threads if name.endswith('.worker')]
    assert not leaked_workers, (
        f"Worker threads survived root.stop(): {leaked_workers}"
    )


def test_worker_exception_sets_error_and_preserves_result(wait_until, free_zmq_port):
    # TEST-06 (#1243): when the worker function raises, str(exc) lands in
    # {name}Error, Running is cleared to False, and Result is left unchanged.
    pr_interfaces.VirtualClient.ClientCache.clear()

    with ZmqIntegrationRoot(port=free_zmq_port) as root:
        client = pr_interfaces.VirtualClient(
            addr='127.0.0.1',
            port=root.zmqServer.port(),
            linkTimeout=5.0,
        )
        try:
            remote_dev = client.root.Dev

            # Pre-call: Error must be empty before any invocation.
            assert remote_dev.AsyncBoomError.get() == "", (
                f"Expected empty AsyncBoomError before call, "
                f"got {remote_dev.AsyncBoomError.get()!r}"
            )

            # Snapshot Result before the call — unchanged-sentinel independent
            # of the chosen default value.
            result_before = remote_dev.AsyncBoomResult.get()

            # Fire the raising command — returns None immediately (nonBlocking).
            remote_dev.AsyncBoom()

            # Wait for the worker to exit after raising.
            assert wait_until(
                lambda: remote_dev.AsyncBoomRunning.get() is False,
                timeout=10.0,
            ), "AsyncBoomRunning never cleared after worker exception"

            # Error carries str(exc) only.
            assert remote_dev.AsyncBoomError.get() == "boom", (
                f"Expected AsyncBoomError='boom', got {remote_dev.AsyncBoomError.get()!r}"
            )

            # Running is False — cleared in the error branch.
            assert remote_dev.AsyncBoomRunning.get() is False, (
                "AsyncBoomRunning should be False after exception"
            )

            # Result is UNCHANGED — the error branch does not update Result.
            assert remote_dev.AsyncBoomResult.get() == result_before, (
                f"Result changed after exception: "
                f"before={result_before!r}, after={remote_dev.AsyncBoomResult.get()!r}"
            )

        finally:
            client.stop()
            pr_interfaces.VirtualClient.ClientCache.clear()
