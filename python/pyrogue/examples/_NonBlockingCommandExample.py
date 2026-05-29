#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       Cookbook: non-blocking Command with client-side polling loop.
#       Demonstrates calling a long-running Command with blocking=False
#       and polling the command's exposed properties via SimpleClient.
#       Run directly:
#           python -m pyrogue.examples._NonBlockingCommandExample
#       Import and call main() from a smoke test for CI coverage.
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
import pyrogue.interfaces as pr_interfaces


def _apply_config(cmd):
    """Simulate a multi-step configuration apply (the long-running work)."""
    steps = [
        ('reset_defaults',   0.3),
        ('load_cal_table',   0.3),
        ('verify_checksums', 0.3),
    ]
    for step, duration in steps:
        cmd._log.info('Config step: %s', step)
        time.sleep(duration)
    return 'configured'


class ConfigDevice(pr.Device):
    """Device that exposes a single long-running ApplyConfig command.

    Any command can be called with ``blocking=False`` to dispatch on a
    worker thread.  The caller polls ``cmd.running``, ``cmd.result``,
    and ``cmd.error`` for completion status.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add(pr.LocalCommand(
            name='ApplyConfig',
            description=(
                'Apply full device configuration (setDefaults-style). '
                'Call with blocking=False to return immediately; poll '
                'the running property for completion.'
            ),
            function=_apply_config,
            retValue='',
        ))


class NonBlockingCommandRoot(pr.Root):
    """Minimal Root wiring up ConfigDevice and a ZmqServer.

    Parameters
    ----------
    port : int
        Base ZMQ port.  0 (default) lets the server auto-assign.
    """

    def __init__(self, *, port=0):
        super().__init__(name='Top', pollEn=False)
        self.add(ConfigDevice(name='Dev'))
        self.zmqServer = pr_interfaces.ZmqServer(root=self, addr='127.0.0.1', port=port)
        self.addInterface(self.zmqServer)


def main(port=0, poll_interval=0.1, timeout=30.0):
    """Run the non-blocking Command example and return the Result string.

    1. Fire the command via SimpleClient.exec(blocking=False).
    2. Poll the command's ``running`` property until False.
    3. Check ``error``; raise RuntimeError if non-empty.
    4. Return ``result``.

    Parameters
    ----------
    port : int
        ZMQ base port passed to NonBlockingCommandRoot.  0 = auto-assign.
    poll_interval : float
        Seconds between polls.
    timeout : float
        Maximum seconds to wait before raising.

    Returns
    -------
    str
        The command's result value on successful completion.
    """
    with NonBlockingCommandRoot(port=port) as root:
        actual_port = root.zmqServer.port()
        with pr_interfaces.SimpleClient(addr='127.0.0.1', port=actual_port) as client:

            client.exec('Top.Dev.ApplyConfig', blocking=False)

            deadline  = time.monotonic() + timeout
            completed = False
            while time.monotonic() < deadline:
                if not client._remoteAttr('Top.Dev.ApplyConfig', 'running'):
                    completed = True
                    break
                time.sleep(poll_interval)

            if not completed:
                raise TimeoutError(
                    f'ApplyConfig did not complete within {timeout:.1f}s')

            error  = client._remoteAttr('Top.Dev.ApplyConfig', 'error')
            result = client._remoteAttr('Top.Dev.ApplyConfig', 'result')

            if error:
                raise RuntimeError(f'ApplyConfig failed: {error}')

            return result


if __name__ == '__main__':
    result = main()
    print(f'ApplyConfig completed: {result}')
