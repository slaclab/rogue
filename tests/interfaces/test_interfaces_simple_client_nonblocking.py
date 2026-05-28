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
            description='Non-blocking config apply — returns immediately.',
            function=_apply_config_fn,
            nonBlocking=True,
            retValue='',
        ))


class NonBlockingRoot(pr.Root):
    def __init__(self, *, port):
        super().__init__(name='Top', pollEn=False)
        self.add(NonBlockingDevice(name='Dev'))
        self.zmqServer = pr_interfaces.ZmqServer(root=self, addr='*', port=port)
        self.addInterface(self.zmqServer)


def test_simpleclient_exec_nonblocking_returns_immediately(wait_until, free_zmq_port):
    # TEST-03: SimpleClient.exec on a nonBlocking=True Command returns immediately
    # (well under the worker's 1-second duration) without raising.  Polling via
    # client.get() shows Running flip True->False and Result population.
    # SimpleClient uses a raw zmq.REQ socket with no recv timeout and no cache.

    with NonBlockingRoot(port=free_zmq_port) as root:
        with pr_interfaces.SimpleClient(addr='127.0.0.1', port=root.zmqServer.port()) as client:
            t0 = time.monotonic()
            result = client.exec('Top.Dev.ApplyConfig')
            elapsed = time.monotonic() - t0

            # (a) exec returns None immediately — well under the 1-second worker duration.
            assert result is None, f"Expected None, got {result!r}"
            assert elapsed < 1.0, (
                f"nonBlocking exec should return immediately but took {elapsed:.2f} s"
            )

            # (b) Running flips to True while the worker is in flight.
            assert wait_until(
                lambda: client.get('Top.Dev.ApplyConfigRunning') is True,
                timeout=5.0,
            ), "ApplyConfigRunning never became True"

            # (c) Running clears once the 1-second worker finishes.
            assert wait_until(
                lambda: client.get('Top.Dev.ApplyConfigRunning') is False,
                timeout=10.0,
            ), "ApplyConfigRunning never returned to False"

            # (d) Result carries the function's return value.
            assert client.get('Top.Dev.ApplyConfigResult') == 'configured', (
                f"Expected 'configured', got {client.get('Top.Dev.ApplyConfigResult')!r}"
            )

            # (e) Error is empty on a successful run.
            assert client.get('Top.Dev.ApplyConfigError') == '', (
                f"Expected empty Error, got {client.get('Top.Dev.ApplyConfigError')!r}"
            )


def test_cookbook_example_runs_headless(free_zmq_port):
    # Smoke test: import and run the cookbook main() headlessly to verify it
    # completes without error and returns the expected Result string.  Prevents
    # the cookbook example from silently rotting.
    from pyrogue.examples._NonBlockingCommandExample import main

    result = main(port=free_zmq_port)
    assert result == 'configured', (
        f"Cookbook example should return 'configured', got {result!r}"
    )
