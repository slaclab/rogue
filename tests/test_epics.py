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
import pyrogue.protocols.epics
from epics import caget, caput
import time

epics_prefix='test_ioc'

class myDevice(pyrogue.Device):
    def __init__(self, name="myDevice", description='My device', **kargs):
        super().__init__(name=name, description=description, **kargs)

        self.add(pyrogue.LocalVariable(
            name='var',
            value=0,
            mode='RW'))

        self.add(pyrogue.LocalVariable(
            name='var_float',
            value=0.0,
            mode='RW'))

class LocalRoot(pyrogue.Root):
    def __init__(self):
        pyrogue.Root.__init__(self, name='LocalRoot', description='Local root', serverPort=None)
        my_device=myDevice()
        self.add(my_device)

class LocalRootWithEpics(LocalRoot):
    def __init__(self, use_map=False):
        LocalRoot.__init__(self)

        if use_map:
            # PV map
            pv_map = { 'LocalRoot.myDevice.var'       : epics_prefix+':LocalRoot:myDevice:var', \
                       'LocalRoot.myDevice.var_float' : epics_prefix+':LocalRoot:myDevice:var_float', \
                    }
        else:
            pv_map=None

        self.epics=pyrogue.protocols.epics.EpicsCaServer(base=epics_prefix, root=self, pvMap=pv_map)
        self.addProtocol(self.epics)


def test_local_root():
    """
    Test Epics Server
    """

    # Test both autogeneration and mapping of PV names
    pv_map_states = [False, True]

    for s in pv_map_states:
        with LocalRootWithEpics(use_map=s) as root:
            time.sleep(1)

            # Device EPICS PV name prefix
            device_epics_prefix=epics_prefix+':LocalRoot:myDevice'

            # Test dump method
            root.epics.dump()

            # Test list method
            root.epics.list()

            # Test RW a variable holding an scalar value
            pv_name=device_epics_prefix+':var'
            test_value=314
            caput(pv_name, test_value)
            test_result=caget(pv_name)
            if test_result != test_value:
               raise AssertionError('pv_name={}: test_value={}; test_result={}'.format(\
                                       pv_name, test_value, test_result))

            # Test RW a variable holding a float value
            pv_name=device_epics_prefix+':var_float'
            test_value=5.67
            caput(pv_name, test_value)
            test_result=round(caget(pv_name),2)
            if test_result != test_value:
               raise AssertionError('pv_name={}: test_value={}; test_result={}'.format(\
                                       pv_name, test_value, test_result))

        # Allow epics client to reset
        time.sleep(5)

    """
    Test EPICS server with a non-started tree
    """
    try:
        root=pyrogue.Root(name='LocalRoot', description='Local root')
        root.epics=pyrogue.protocols.epics.EpicsCaServer(base=epics_prefix, root=root)
        root.epics.start()
        raise AssertionError('Attaching a pyrogue.epics to a non-started tree did not throw exception')
    except Exception as e:
        pass

    """
    Test createMaster and createSlave methods
    """
    with LocalRootWithEpics() as root:
        slave=root.epics.createSlave(name='slave', maxSize=1000, type='UInt16')
        master=root.epics.createMaster(name='master', maxSize=1000, type='UInt16')

if __name__ == "__main__":
    test_local_root()

