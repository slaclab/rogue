#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import pyrogue

# Test values
ro_set=314
min_set=1.0
max_set=100.0
poll_set=1.0
enum_set={0:'zero', 1:'one'}

class myDevice(pyrogue.Device):
    def __init__(self, name="myDevice", description='My device', **kargs):
        super().__init__(name=name, description=description, **kargs)

        self.add(pyrogue.LocalVariable(
            name='var',
            value=0.0,
            mode='RW'))

        self.add(pyrogue.LocalVariable(
            name='var_ro',
            value=314,
            mode='RO'))

        self.add(pyrogue.LocalVariable(
            name='var_array',
            value=[0]*5,
            mode='RW'))

        self.add(pyrogue.LocalVariable(
            name='var_enum',
            enum=enum_set,
            value=0,
        ))

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

        self.add(pyrogue.LocalVariable(
            name='var_with_properties',
            value=0.0,
            mode='RW',
            minimum=min_set,
            maximum=max_set))

        # Test a variable with a disp list
        self.add(pyrogue.LocalVariable(
            name='var_with_disp',
            disp=['on', 'off'],
            value=0))

        # Try to define a variable without value, which should raise an exception
        try:
            self.add(pyrogue.LocalVariable(
                name='var_without_value'))
            raise AssertionError('Adding a local variable without value did not raise an exception')
        except Exception as e:
            pass

        # Test to define a variable with an invalid mode
        try:
            self.add(pyrogue.LocalVariable(
                name='var_with_invalid_mode',
                value=0,
                mode='INV'))
            raise AssertionError('Adding a local variable with invalid mode did not raise an exception')
        except Exception as e:
            pass

class LocalRoot(pyrogue.Root):
    def __init__(self):
        pyrogue.Root.__init__(self, name='LocalRoot', description='Local root',serverPort=None)
        my_device=myDevice()
        self.add(my_device)

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
            raise AssertionError('Value written was {}, but value read back was = {}'.format(test_value, test_result))

        # Test RO a variable holding an scalar value
        test_result=root.myDevice.var_ro.get()
        if test_result != ro_set:
            raise AssertionError('Value set was {}, but value read back was = {}'.format(ro_set, test_result))

        test_value=ro_set+1
        root.myDevice.var_ro.set(test_value)
        if test_result != ro_set:
            raise AssertionError('Able to modify a RO variable. Initial value set was {}, new set value was {}, and value read back was = {}'.format(ro_set, test_value, test_result))

        # Test RW a variable holding an array value
        test_value=[1, 2, 3, 4, 5]
        root.myDevice.var_array.set(test_value)
        test_result=root.myDevice.var_array.get()
        if test_result != test_value:
            raise AssertionError('Value written was {}, but value read back was = {}'.format(test_value, test_result))

        # Test RW a variable holding an enum
        for test_raw,test_enum in enum_set.items():
            # Test setting the raw value and reading back both
            root.myDevice.var_enum.set(test_raw)
            result_raw=root.myDevice.var_enum.get()
            if result_raw != test_raw:
                raise AssertionError('Raw value set to {}, but raw value read back was {}'.format(test_raw, result_raw))

            result_enum=root.myDevice.var_enum.getDisp()
            if result_enum != test_enum:
                raise AssertionError('Raw value set to {}, but enum value read back was \"{}\" instead of \"{}\"'.format(test_raw, result_enum, test_enum))

            # Test setting the enum value and reading back both
            root.myDevice.var_enum.setDisp(test_enum)
            result_raw=root.myDevice.var_enum.get()
            if result_raw != test_raw:
                raise AssertionError('Enum value set to \"{}\", but raw value read back was {} instead of {}'.format(test_enum, result_raw, test_raw))

            result_enum=root.myDevice.var_enum.getDisp()
            if result_enum != test_enum:
                raise AssertionError('Enum value set to \"{}\", but enum value read back was \"{}\"'.format(test_enum, result_enum))

        # Test RW a link variable holding an scalar value
        test_value=5.6
        root.myDevice.var_link.set(test_value)
        test_result=root.myDevice.var_link.get()
        if test_result != test_value:
            raise AssertionError('Value written was {}, but value read back was = {}'.format(test_value, test_result))

        # Test RW a link variable holding an array value
        test_value=[6, 7, 8, 9, 10]
        root.myDevice.var_array_link.set(test_value)
        test_result=root.myDevice.var_array_link.get()
        if test_result != test_value:
            raise AssertionError('Value written was {}, but value read back was = {}'.format(test_value, test_result))

        # Check pollInterval set/readback methods
        root.myDevice.var_with_properties.pollInterval=poll_set
        poll_read=root.myDevice.var_with_properties.pollInterval
        if poll_read != poll_set:
            raise AssertionError('Poll Interval was set to {} was was read back as {}'. format(poll_set,poll_read))

        # Verify that minimum and maximum readbacks are correct
        min_read=root.myDevice.var_with_properties.minimum
        if min_read != min_set:
            raise AssertionError('Minimum was set to {} but was read as {}'.format(min_set, min_read))

        max_read=root.myDevice.var_with_properties.maximum
        if max_read != max_set:
            raise AssertionError('Minimum was set to {} but was read as {}'.format(max_set, max_read))

if __name__ == "__main__":
    test_local_root()

