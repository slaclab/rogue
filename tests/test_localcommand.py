#!/usr/bin/env python3

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
            description='Commad running in the foreground',
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
        pyrogue.Root.__init__(self, name='LocalRoot', description='Local root')
        my_device=myDevice()
        self.add(my_device)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

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
            raise AssertionError('Comamnd running in foreground returned too soon: '
                'delay was set to {} s, and the command took {} s.'.format(delay, duration))

        # Test a local command running in the background
        start=time()
        root.myDevice.cmd_bg.call(2)
        end=time()
        duration=end-start
        if duration > delay:
            raise AssertionError('Comamnd running in background returned too late: '
                'delay was set to {} s, and the command took {} s.'.format(delay, duration))
