#!/usr/bin/env python3

import pyrogue
import rogue
import unittest

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
        my_device = myDevice()
        self.add(my_device)

class Root(unittest.TestCase):
    """
    Test Pyrogue
    """
    root = LocalRoot()
    root.start()
    reutl = root.myDevice.var.get()
    root.stop()

    self.assertEqual(result, 3.14)

if __name__ == "__main__":
    unittest.main()