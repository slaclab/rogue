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

import pytest
import pyrogue as pr
import pyrogue.interfaces as pr_interfaces


pytestmark = pytest.mark.integration


def _apply_config_fn():
    """Simulate a multi-step configuration apply (1 second total)."""
    time.sleep(1.0)
    return 'configured'


class NonBlockingDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add(pr.LocalCommand(
            name='ApplyConfig',
            description='Config apply command.',
            function=_apply_config_fn,
            retValue='',
        ))


class NonBlockingRoot(pr.Root):
    def __init__(self, *, port):
        super().__init__(name='Top', pollEn=False)
        self.add(NonBlockingDevice(name='Dev'))
        self.zmqServer = pr_interfaces.ZmqServer(root=self, addr='*', port=port)
        self.addInterface(self.zmqServer)


def test_simpleclient_exec_nonblocking_returns_immediately(wait_until, free_zmq_port):
    """SimpleClient.exec(blocking=False) returns immediately. Status is
    polled via _remoteAttr on the exposed command properties."""

    with NonBlockingRoot(port=free_zmq_port) as root:
        with pr_interfaces.SimpleClient(addr='127.0.0.1', port=root.zmqServer.port()) as client:
            t0 = time.monotonic()
            result = client.exec('Top.Dev.ApplyConfig', blocking=False)
            elapsed = time.monotonic() - t0

            assert result is None, f"Expected None, got {result!r}"
            assert elapsed < 1.0, (
                f"blocking=False exec should return immediately but took {elapsed:.2f} s"
            )

            assert wait_until(
                lambda: client._remoteAttr('Top.Dev.ApplyConfig', 'running') is True,
                timeout=5.0,
            ), "running never became True"

            assert wait_until(
                lambda: client._remoteAttr('Top.Dev.ApplyConfig', 'running') is False,
                timeout=10.0,
            ), "running never returned to False"

            assert client._remoteAttr('Top.Dev.ApplyConfig', 'result') == 'configured', (
                f"Expected 'configured', got {client._remoteAttr('Top.Dev.ApplyConfig', 'result')!r}"
            )

            assert client._remoteAttr('Top.Dev.ApplyConfig', 'error') == '', (
                f"Expected empty error, got {client._remoteAttr('Top.Dev.ApplyConfig', 'error')!r}"
            )


def test_cookbook_example_runs_headless(free_zmq_port):
    """Smoke test: the cookbook example completes without error."""
    from pyrogue.examples._NonBlockingCommandExample import main

    result = main(port=free_zmq_port)
    assert result == 'configured', (
        f"Cookbook example should return 'configured', got {result!r}"
    )
