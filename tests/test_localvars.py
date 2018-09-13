#!/usr/bin/env python3

import pyrogue

class myDevice(pyrogue.Device):
    def __init__(self, name="myDevice", description='My device', **kargs):
        super().__init__(name=name, description=description, **kargs)

        self.add(pyrogue.LocalVariable(
            name='var',
            value=3.14,
            mode='RW'))

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

def test_local_root():
    """
    Test Pyrogue
    """
    with LocalRoot() as root:
        
        # Test RW a variable holding an scalar value
        test_value=3.14
        root.myDevice.var.set(test_value)
        test_result=root.myDevice.var.get()
        if test_result != test_value:
            raise AssertionError()
