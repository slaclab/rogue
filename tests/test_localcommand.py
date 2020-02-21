#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

from time import time, sleep

import pyrogue

# Test values
delay=2

class myDevice(pyrogue.Device):
    def __init__(self, name="myDevice", description='My device', **kargs):
        super().__init__(name=name, description=description, **kargs)

        # This command calls _DelayFunction in the foreground
        self.add(pyrogue.LocalCommand(
            name='cmd_fg',
            description='Command running in the foreground',
            function=self._DelayFunction))

        # This command calls _DelayFunction in the background
        self.add(pyrogue.LocalCommand(
            name='cmd_bg',
            description='Command running in the background',
            background=True,
            function=self._DelayFunction))

    # Blocking function. The passed argument specify how many seconds
    # it will block.
    def _DelayFunction(self,arg):
        sleep(arg)

class LocalRoot(pyrogue.Root):
    def __init__(self):
        pyrogue.Root.__init__(self, name='LocalRoot', description='Local root',serverPort=None)
        my_device=myDevice()
        self.add(my_device)

def test_local_cmd():
    """
    Test Local Commands
    """
    with LocalRoot() as root:

        # Test a local command running in the foreground
        start=time()
        root.myDevice.cmd_fg.call(delay)
        end=time()
        duration=end-start
        if duration < delay:
            raise AssertionError('Command running in foreground returned too soon: '
                'delay was set to {} s, and the command took {} s.'.format(delay, duration))

        # Test a local command running in the background
        start=time()
        root.myDevice.cmd_bg.call(2)
        end=time()
        duration=end-start
        if duration > delay:
            raise AssertionError('Command running in background returned too late: '
                'delay was set to {} s, and the command took {} s.'.format(delay, duration))

if __name__ == "__main__":
    test_local_cmd()

