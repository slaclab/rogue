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


class _LogRecorder:
    """Minimal logger stub that records warning() calls."""

    def __init__(self):
        self.messages = []

    def warning(self, message):
        self.messages.append(message)

    def __getattr__(self, name):
        return lambda *a, **k: None


def raise_boom():
    raise RuntimeError("boom")


def _async_sleep_fn():
    time.sleep(2.0)
    return 'done'


class ZmqIntegrationDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.add(pr.LocalCommand(
            name='SyncSleep',
            description='Synchronous sleep.',
            function=lambda: time.sleep(3),
        ))

        self.add(pr.LocalCommand(
            name='AsyncSleep',
            description='Used with blocking=False.',
            function=_async_sleep_fn,
            retValue='',
        ))

        self.add(pr.LocalCommand(
            name='SyncMul',
            description='Synchronous multiply.',
            value=0,
            retValue=0,
            function=lambda arg: arg * 3,
        ))

        self.add(pr.LocalCommand(
            name='AsyncSlow',
            description='2-second sleep for re-entry test.',
            function=lambda: time.sleep(2.0),
            retValue='',
        ))

        self.add(pr.LocalCommand(
            name='AsyncLong',
            description='5-second sleep for shutdown test.',
            function=lambda: time.sleep(5.0),
            retValue='',
        ))

        self.add(pr.LocalCommand(
            name='AsyncBoom',
            description='Raises RuntimeError for error-path test.',
            function=raise_boom,
        ))


class ZmqIntegrationRoot(pr.Root):
    def __init__(self, *, port):
        super().__init__(name='Top', pollEn=False)
        self.add(ZmqIntegrationDevice(name='Dev'))

        self.zmqServer = pr_interfaces.ZmqServer(root=self, addr='*', port=port)
        self.addInterface(self.zmqServer)


def test_sync_command_baseline_blocks_link(free_zmq_port):
    """Synchronous call blocks the client for the full duration."""
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
            assert elapsed >= 2.5, (
                f"Sync command should block for ~3 s but returned in {elapsed:.2f} s"
            )
        finally:
            client.stop()
            pr_interfaces.VirtualClient.ClientCache.clear()


def test_nonblocking_command_returns_immediately(wait_until, free_zmq_port):
    """blocking=False returns immediately; status is polled via exposed
    properties on the command node."""
    pr_interfaces.VirtualClient.ClientCache.clear()

    with ZmqIntegrationRoot(port=free_zmq_port) as root:
        client = pr_interfaces.VirtualClient(
            addr='127.0.0.1',
            port=root.zmqServer.port(),
            linkTimeout=2.0,
        )
        try:
            remote_cmd = client.root.Dev.AsyncSleep

            t0 = time.monotonic()
            remote_cmd(blocking=False)
            elapsed = time.monotonic() - t0

            assert elapsed < 1.0, (
                f"blocking=False should return immediately but took {elapsed:.2f} s"
            )

            assert wait_until(
                lambda: remote_cmd.running is True,
                timeout=5.0,
            ), "running never became True"

            assert wait_until(
                lambda: remote_cmd.running is False,
                timeout=10.0,
            ), "running never returned to False"

            assert remote_cmd.result == 'done', (
                f"Expected result='done', got {remote_cmd.result!r}"
            )

            assert remote_cmd.error == '', (
                f"Expected empty error, got {remote_cmd.error!r}"
            )
        finally:
            client.stop()
            pr_interfaces.VirtualClient.ClientCache.clear()


def test_sync_command_returns_value(free_zmq_port):
    """Default blocking=True returns the function value synchronously."""
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
    """A second blocking=False call while the worker is running is rejected."""
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
            remote_cmd = client.root.Dev.AsyncSlow

            result_before = remote_cmd.result

            remote_cmd(blocking=False)

            assert wait_until(
                lambda: remote_cmd.running is True,
                timeout=5.0,
            ), "running never became True after first call"

            result = remote_cmd(blocking=False)
            assert result is None

            assert recorder.messages == ["Command already running!"]

            worker_threads = [
                t for t in threading.enumerate()
                if t.name == f'{cmd.path}.worker'
            ]
            assert len(worker_threads) == 1

            assert remote_cmd.result == result_before

            assert wait_until(
                lambda: remote_cmd.running is False,
                timeout=10.0,
            ), "running never returned to False"

        finally:
            cmd._log = original_log
            client.stop()
            pr_interfaces.VirtualClient.ClientCache.clear()


def test_root_stop_joins_in_flight_worker(wait_until, free_zmq_port):
    """Root.stop() joins any in-flight worker thread."""
    pr_interfaces.VirtualClient.ClientCache.clear()

    with ZmqIntegrationRoot(port=free_zmq_port) as root:
        client = pr_interfaces.VirtualClient(
            addr='127.0.0.1',
            port=root.zmqServer.port(),
            linkTimeout=10.0,
        )
        try:
            remote_cmd = client.root.Dev.AsyncLong

            remote_cmd(blocking=False)

            assert wait_until(
                lambda: remote_cmd.running is True,
                timeout=5.0,
            ), "running never became True"

        finally:
            client.stop()
            pr_interfaces.VirtualClient.ClientCache.clear()

    post_threads = {t.name for t in threading.enumerate()}
    leaked_workers = [name for name in post_threads if name.endswith('.worker')]
    assert not leaked_workers, (
        f"Worker threads survived root.stop(): {leaked_workers}"
    )


def test_worker_exception_sets_error_and_preserves_result(wait_until, free_zmq_port):
    """When the worker raises, error captures str(exc) and result is unchanged."""
    pr_interfaces.VirtualClient.ClientCache.clear()

    with ZmqIntegrationRoot(port=free_zmq_port) as root:
        client = pr_interfaces.VirtualClient(
            addr='127.0.0.1',
            port=root.zmqServer.port(),
            linkTimeout=5.0,
        )
        try:
            remote_cmd = client.root.Dev.AsyncBoom

            assert remote_cmd.error == ''

            result_before = remote_cmd.result

            remote_cmd(blocking=False)

            assert wait_until(
                lambda: remote_cmd.running is False,
                timeout=10.0,
            ), "running never cleared after worker exception"

            assert remote_cmd.error == "boom"
            assert remote_cmd.running is False
            assert remote_cmd.result == result_before

        finally:
            client.stop()
            pr_interfaces.VirtualClient.ClientCache.clear()
