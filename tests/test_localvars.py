#!/usr/bin/env python3

import pyrogue

class myDevice(pyrogue.Device):
    def __init__(self, name="myDevice", description='My device', **kargs):
        super().__init__(name=name, description=description, **kargs)

        self.add(pyrogue.LocalVariable(
            name='var',
            value=0.0,
            mode='RW'))

        self.add(pyrogue.LocalVariable(
            name='var_array',
            value=[0]*5,
            mode='RW'))

        self.add(pyrogue.LinkVariable(
            name='var_link',
            mode='RW',
            linkedSet=lambda dev, var, value: var.dependencies[0].set(value),
            linkedGet=lambda dev, var: var.dependencies[0].value(),
            dependencies=[self.variables['var']]))

        self.add(pyrogue.LinkVariable(
            name='var_array_link',
            mode='RW',
            linkedSet=lambda dev, var, value: var.dependencies[0].set(value),
            linkedGet=lambda dev, var: var.dependencies[0].value(),
            dependencies=[self.variables['var_array']]))

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

        # Test RW a variable holding an array value
        test_value=[1, 2, 3, 4, 5]
        root.myDevice.var_array.set(test_value)
        test_result=root.myDevice.var_array.get()
        if test_result != test_value:
            raise AssertionError()

        # Test RW a link variable holding an scalue value
        test_value=5.6
        root.myDevice.var_link.set(test_value)
        test_result=root.myDevice.var_link.get()
        if test_result != test_value:
            raise AssertionError()

        # Test RW a link variable holding an array value
        test_value=[6, 7, 8, 9, 10]
        root.myDevice.var_array_link.set(test_value)
        test_result=root.myDevice.var_array_link.get()
        if test_result != test_value:
            raise AssertionError()
