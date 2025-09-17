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

import time
import pyrogue as pr
import pyrogue.protocols.epicsV4
import rogue.interfaces.memory

from p4p.client.thread import Context

epics_prefix='test_ioc'

class SimpleDev(pr.Device):

    def __init__(self,**kwargs):

        super().__init__(**kwargs)

        self.add(pr.LocalVariable(
            name  = 'LocalRwInt',
            value = 0,
            mode  = 'RW'))

        self.add(pr.LocalVariable(
            name  = 'LocalWoInt',
            value = 0,
            mode  = 'WO'))

        self.add(pr.LocalVariable(
            name  = 'LocalRwFloat',
            value = 0.0,
            mode  = 'RW'))

        self.add(pr.RemoteVariable(
            name      = "RemoteRwInt",
            offset    = 0x000,
            value     = 0,
            mode      = "RW",
        ))

        self.add(pr.RemoteVariable(
            name      = "RemoteWoInt",
            offset    = 0x004,
            value     = 0,
            mode      = "WO",
        ))


class LocalRoot(pr.Root):
    def __init__(self):
        pr.Root.__init__(self, name='LocalRoot', description='Local root')

        pr.Root.__init__(self,
                         name='LocalRoot',
                         description='Local root',
                         timeout=2.0,
                         pollEn=False)

        # Use a memory space emulator
        sim = rogue.interfaces.memory.Emulate(4,0x1000)
        self.addInterface(sim)

        # Create a memory gateway
        ms = rogue.interfaces.memory.TcpServer("127.0.0.1",9070)
        self.addInterface(ms)

        # Connect the memory gateways together
        sim << ms

        # Create a memory gateway
        mc = rogue.interfaces.memory.TcpClient("127.0.0.1",9070)
        self.addInterface(mc)

        # Add Device
        self.add(SimpleDev(
            name    = 'SimpleDev',
            offset  = 0x0000,
            memBase = mc,
        ))

class LocalRootWithEpics(LocalRoot):
    def __init__(self, use_map=False):
        LocalRoot.__init__(self)

        if use_map:
            # PV map
            pv_map = {
                'LocalRoot.SimpleDev.LocalRwInt'   : epics_prefix+':LocalRoot:SimpleDev:LocalRwInt',
                'LocalRoot.SimpleDev.LocalWoInt'   : epics_prefix+':LocalRoot:SimpleDev:LocalWoInt',
                'LocalRoot.SimpleDev.LocalRwFloat' : epics_prefix+':LocalRoot:SimpleDev:LocalRwFloat',
                'LocalRoot.SimpleDev.RemoteRwInt'  : epics_prefix+':LocalRoot:SimpleDev:RemoteRwInt',
                'LocalRoot.SimpleDev.RemoteWoInt'  : epics_prefix+':LocalRoot:SimpleDev:RemoteWoInt',
            }
        else:
            pv_map=None

        self.epics = pyrogue.protocols.epicsV4.EpicsPvServer(
            base      = epics_prefix,
            root      = self,
            pvMap     = pv_map,
            incGroups = None,
            excGroups = None,
        )
        self.addProtocol(self.epics)

def test_local_root():
    """
    Test Epics Server
    """
    # Test both autogeneration and mapping of PV names
    pv_map_states = [False, True]

    # setup the P4P client
    # https://mdavidsaver.github.io/p4p/client.html#usage
    print( Context.providers() )
    ctxt = Context('pva')

    for s in pv_map_states:
        with LocalRootWithEpics(use_map=s) as root:
            time.sleep(1)

            # Device EPICS PV name prefix
            device_epics_prefix=epics_prefix+':LocalRoot:SimpleDev'

            # Test dump method
            root.epics.dump()

            # Test list method
            root.epics.list()
            time.sleep(1)

            # Test RW a variable holding an scalar value
            pv_name=device_epics_prefix+':LocalRwInt'
            test_value=314
            ctxt.put(pv_name, test_value)
            time.sleep(1)
            test_result=ctxt.get(pv_name)
            if test_result != test_value:
                raise AssertionError('pv_name={}: test_value={}; test_result={}'.format(pv_name, test_value, test_result))

            # Test WO a variable holding an scalar value
            pv_name=device_epics_prefix+':LocalWoInt'
            test_value=314
            ctxt.put(pv_name, test_value)

            # Test RW a variable holding a float value
            pv_name=device_epics_prefix+':LocalRwFloat'
            test_value=5.67
            ctxt.put(pv_name, test_value)
            time.sleep(1)
            test_result=round(ctxt.get(pv_name),2)
            if test_result != test_value:
                raise AssertionError('pvStates={} pv_name={}: test_value={}; test_result={}'.format(s, pv_name, test_value, test_result))

            # Test RW a variable holding an scalar value
            pv_name=device_epics_prefix+':RemoteRwInt'
            test_value=314
            ctxt.put(pv_name, test_value)
            time.sleep(1)
            test_result=ctxt.get(pv_name)
            if test_result != test_value:
                raise AssertionError('pv_name={}: test_value={}; test_result={}'.format(pv_name, test_value, test_result))

            # Test WO a variable holding an scalar value
            pv_name=device_epics_prefix+':RemoteWoInt'
            test_value=314
            ctxt.put(pv_name, test_value)

        # Allow epics client to reset
        time.sleep(5)

if __name__ == "__main__":
    test_local_root()
