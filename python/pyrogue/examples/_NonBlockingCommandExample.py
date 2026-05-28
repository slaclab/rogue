#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       Cookbook: non-blocking Command with client-side polling loop.
#       Demonstrates a setDefaults-shaped configuration-apply Command using
#       nonBlocking=True and the matching hand-rolled polling loop driven by
#       SimpleClient.  Run directly:
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
    """Simulate a multi-step configuration apply (the long-running work).

    Models a setDefaults-style operation: iterate over named steps, each
    with a short delay to simulate real register/DMA traffic, then return
    a status string that populates the ApplyConfigResult sibling variable.
    """
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

    The command is marked nonBlocking=True so that ZMQ clients (e.g.
    SimpleClient, VirtualClient) receive None immediately and can poll
    the ApplyConfigRunning / ApplyConfigResult / ApplyConfigError sibling
    variables for completion status.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add(pr.LocalCommand(
            name='ApplyConfig',
            description=(
                'Apply full device configuration (setDefaults-style). '
                'Returns immediately; poll ApplyConfigRunning for completion. '
                'Result is available in ApplyConfigResult once Running is False.'
            ),
            function=_apply_config,
            nonBlocking=True,
            retValue='',
        ))


class NonBlockingCommandRoot(pr.Root):
    """Minimal Root wiring up ConfigDevice and a ZmqServer.

    Parameters
    ----------
    port : int
        Base ZMQ port.  0 (default) lets the server auto-assign from 9099
        upward.  Pass an explicit port when the caller must control binding
        (e.g. in a smoke test that supplies a free port).
    """

    def __init__(self, *, port=0):
        super().__init__(name='Top', pollEn=False)
        self.add(ConfigDevice(name='Dev'))
        self.zmqServer = pr_interfaces.ZmqServer(root=self, addr='127.0.0.1', port=port)
        self.addInterface(self.zmqServer)


def main(port=0, poll_interval=0.1, timeout=30.0):
    """Run the non-blocking Command example and return the Result string.

    This function is the canonical reference shape for the hand-rolled
    client-side polling loop that pairs with a nonBlocking=True Command:

    1. Fire the command via SimpleClient.exec — returns None immediately.
    2. Poll ApplyConfigRunning until it becomes False (bounded by timeout).
    3. Read ApplyConfigError; raise RuntimeError if non-empty.
    4. Return ApplyConfigResult.

    Parameters
    ----------
    port : int
        ZMQ base port passed to NonBlockingCommandRoot.  0 = auto-assign.
    poll_interval : float
        Seconds between ApplyConfigRunning polls.
    timeout : float
        Maximum seconds to wait for the command to finish before raising.

    Returns
    -------
    str
        The value stored in ApplyConfigResult on successful completion.
    """
    with NonBlockingCommandRoot(port=port) as root:
        actual_port = root.zmqServer.port()
        with pr_interfaces.SimpleClient(addr='127.0.0.1', port=actual_port) as client:

            # Fire the long-running command — returns None immediately because
            # the server dispatches a worker thread and replies before it finishes.
            client.exec('Top.Dev.ApplyConfig')

            # Hand-rolled polling loop: the canonical pattern for nonBlocking Commands.
            # Poll the auto-injected ApplyConfigRunning sibling variable until it
            # transitions to False, indicating the worker thread has completed.
            deadline  = time.monotonic() + timeout
            completed = False
            while time.monotonic() < deadline:
                if not client.get('Top.Dev.ApplyConfigRunning'):
                    completed = True
                    break
                time.sleep(poll_interval)

            if not completed:
                raise TimeoutError(
                    f'ApplyConfig did not complete within {timeout:.1f}s')

            error  = client.get('Top.Dev.ApplyConfigError')
            result = client.get('Top.Dev.ApplyConfigResult')

            if error:
                raise RuntimeError(f'ApplyConfig failed: {error}')

            return result


if __name__ == '__main__':
    result = main()
    print(f'ApplyConfig completed: {result}')
