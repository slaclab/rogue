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
import pyrogue.protocols.epicsV7
import rogue.interfaces.memory

from p4p.client.thread import Context

epics_prefix = 'test_ioc_v7'
PropagateTimeout = 10.0
_read_counter = [0]


class SimpleDev(pr.Device):

    def __init__(self, **kwargs):

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

        self.add(pr.LocalCommand(
            name        = 'ResetLocalRwInt',
            function    = lambda dev: dev.LocalRwInt.set(0),
            description = 'Reset LocalRwInt to 0',
        ))

        self.add(pr.LocalCommand(
            name        = 'SetLocalRwInt',
            function    = lambda dev, arg: dev.LocalRwInt.set(arg),
            description = 'Set LocalRwInt to arg value',
        ))

        self.add(pr.RemoteVariable(
            name   = 'RemoteRwInt',
            offset = 0x000,
            value  = 0,
            mode   = 'RW',
        ))

        self.add(pr.RemoteVariable(
            name   = 'RemoteWoInt',
            offset = 0x004,
            value  = 0,
            mode   = 'WO',
        ))


class LocalRoot(pr.Root):
    def __init__(self):
        pr.Root.__init__(self,
                         name='LocalRoot',
                         description='Local root',
                         timeout=2.0,
                         pollEn=False)

        # Use a memory space emulator
        sim = rogue.interfaces.memory.Emulate(4, 0x1000)
        self.addInterface(sim)

        # Create a memory gateway server
        ms = rogue.interfaces.memory.TcpServer("127.0.0.1", 9075)
        self.addInterface(ms)

        # Connect the memory gateways together
        sim << ms

        # Create a memory gateway client
        mc = rogue.interfaces.memory.TcpClient("127.0.0.1", 9075, True)
        self.memClient = mc
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
            # Explicit PV map
            pv_map = {
                'LocalRoot.SimpleDev.LocalRwInt'      : epics_prefix + ':LocalRoot:SimpleDev:LocalRwInt',
                'LocalRoot.SimpleDev.LocalWoInt'      : epics_prefix + ':LocalRoot:SimpleDev:LocalWoInt',
                'LocalRoot.SimpleDev.LocalRwFloat'    : epics_prefix + ':LocalRoot:SimpleDev:LocalRwFloat',
                'LocalRoot.SimpleDev.RemoteRwInt'     : epics_prefix + ':LocalRoot:SimpleDev:RemoteRwInt',
                'LocalRoot.SimpleDev.RemoteWoInt'     : epics_prefix + ':LocalRoot:SimpleDev:RemoteWoInt',
                'LocalRoot.SimpleDev.ResetLocalRwInt' : epics_prefix + ':LocalRoot:SimpleDev:ResetLocalRwInt',
                'LocalRoot.SimpleDev.SetLocalRwInt'   : epics_prefix + ':LocalRoot:SimpleDev:SetLocalRwInt',
            }
        else:
            pv_map = None

        self.epics = pyrogue.protocols.epicsV7.EpicsPvServer(
            base      = epics_prefix,
            root      = self,
            pvMap     = pv_map,
            incGroups = None,
            excGroups = None,
        )
        self.addProtocol(self.epics)


class DevWithCounter(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        _read_counter[0] = 0

        def counter_get(dev, var):
            _read_counter[0] += 1
            return _read_counter[0]

        self.add(pr.LocalVariable(
            name     = 'IncrOnRead',
            value    = 0,
            mode     = 'RW',
            localGet = counter_get,
        ))


class LocalRootWithCounter(pr.Root):
    def __init__(self):
        pr.Root.__init__(self,
                         name='LocalRoot',
                         description='Local root with counter',
                         timeout=2.0,
                         pollEn=False)

        # Use a memory space emulator
        sim = rogue.interfaces.memory.Emulate(4, 0x1000)
        self.addInterface(sim)

        # Create a memory gateway server
        ms = rogue.interfaces.memory.TcpServer("127.0.0.1", 9075)
        self.addInterface(ms)

        # Connect the memory gateways together
        sim << ms

        # Create a memory gateway client
        mc = rogue.interfaces.memory.TcpClient("127.0.0.1", 9075, True)
        self.memClient = mc
        self.addInterface(mc)

        # Add counter device
        self.add(DevWithCounter(
            name    = 'CounterDev',
            offset  = 0x0000,
            memBase = mc,
        ))

        self.epics = pyrogue.protocols.epicsV7.EpicsPvServer(
            base      = epics_prefix,
            root      = self,
            pvMap     = None,
            incGroups = None,
            excGroups = None,
        )
        self.addProtocol(self.epics)


# TEST-10: convergence helper
def wait_pv_value(ctxt, pv_name, expected, timeout=PropagateTimeout, transform=None):
    start = time.time()

    while True:
        try:
            value = ctxt.get(pv_name)
            if transform is not None:
                value = transform(value)
            if value == expected:
                return
        except Exception:
            pass

        if (time.time() - start) > timeout:
            raise AssertionError('Timed out waiting for pv_name={} expected={} last={}'.format(
                pv_name,
                expected,
                value if 'value' in locals() else 'unavailable'))

        time.sleep(0.1)


def test_local_root():
    """Test EpicsV7 Server -- put/get round-trips, WO, float, remote, commands, both map modes"""

    # Test both autogeneration (pvMap=None) and explicit pvMap modes
    pv_map_states = [False, True]

    # Single context created once; softioc IOC is a process singleton
    print(Context.providers())
    ctxt = Context('pva')

    for s in pv_map_states:
        with LocalRootWithEpics(use_map=s) as root:
            # Device EPICS PV name prefix
            device_epics_prefix = epics_prefix + ':LocalRoot:SimpleDev'

            # Test dump method
            root.epics.dump()

            # Test list method
            root.epics.list()

            # TEST-01: Wait for PVs to become visible through the EPICS server (TEST-10 coverage)
            wait_pv_value(ctxt, device_epics_prefix + ':LocalRwInt', 0)

            # TEST-02: RW a variable holding a scalar int value
            pv_name = device_epics_prefix + ':LocalRwInt'
            test_value = 314
            ctxt.put(pv_name, test_value)
            wait_pv_value(ctxt, pv_name, test_value)  # TEST-10 coverage
            test_result = ctxt.get(pv_name)
            if test_result != test_value:
                raise AssertionError('pv_name={}: test_value={}; test_result={}'.format(
                    pv_name, test_value, test_result))

            # TEST-03: WO a variable holding a scalar int value
            pv_name = device_epics_prefix + ':LocalWoInt'
            test_value = 314
            ctxt.put(pv_name, test_value)

            # TEST-04: RW a variable holding a float value
            pv_name = device_epics_prefix + ':LocalRwFloat'
            test_value = 5.67
            ctxt.put(pv_name, test_value)
            wait_pv_value(ctxt, pv_name, test_value, transform=lambda value: round(value, 2))  # TEST-10 coverage
            test_result = round(ctxt.get(pv_name), 2)
            if test_result != test_value:
                raise AssertionError('pvStates={} pv_name={}: test_value={}; test_result={}'.format(
                    s, pv_name, test_value, test_result))

            # TEST-05: RW a remote variable holding a scalar int value
            pv_name = device_epics_prefix + ':RemoteRwInt'
            test_value = 314
            ctxt.put(pv_name, test_value)
            wait_pv_value(ctxt, pv_name, test_value)  # TEST-10 coverage
            test_result = ctxt.get(pv_name)
            if test_result != test_value:
                raise AssertionError('pv_name={}: test_value={}; test_result={}'.format(
                    pv_name, test_value, test_result))

            # TEST-06: WO a remote variable holding a scalar int value
            pv_name = device_epics_prefix + ':RemoteWoInt'
            test_value = 314
            ctxt.put(pv_name, test_value)

            # TEST-07: Commands invoked via caput (ctxt.put), NOT ctxt.rpc()
            # No-arg command: set LocalRwInt non-zero, then reset via caput with value=0
            pv_name = device_epics_prefix + ':LocalRwInt'
            reset_pv = device_epics_prefix + ':ResetLocalRwInt'
            test_value = 42
            ctxt.put(pv_name, test_value)
            wait_pv_value(ctxt, pv_name, test_value)  # TEST-10 coverage
            ctxt.put(reset_pv, 0)  # value=0 triggers no-arg command call
            wait_pv_value(ctxt, pv_name, 0)  # TEST-10 coverage
            test_result = ctxt.get(pv_name)
            if test_result != 0:
                raise AssertionError('Command reset failed: pv_name={}: expected=0; test_result={}'.format(
                    pv_name, test_result))

            # TEST-07 (with-arg): caput with non-zero value sets LocalRwInt to that value
            set_pv = device_epics_prefix + ':SetLocalRwInt'
            test_value = 99
            ctxt.put(set_pv, test_value)
            wait_pv_value(ctxt, pv_name, test_value)  # TEST-10 coverage
            test_result = ctxt.get(pv_name)
            if test_result != test_value:
                raise AssertionError('Command set failed: pv_name={}: expected={}; test_result={}'.format(
                    pv_name, test_value, test_result))

    # TEST-08: explicit pvMap mode assertions are covered by the use_map=True iteration above

    ctxt.close()


def test_increment_on_read():
    """Test hardware-read-on-get: LocalVariable with localGet counter returns incrementing values on consecutive gets"""

    with LocalRootWithCounter() as root:
        ctxt2 = Context('pva')
        pv_name = epics_prefix + ':LocalRoot:CounterDev:IncrOnRead'

        # Wait for PV to become available (TEST-10 coverage)
        wait_pv_value(ctxt2, pv_name, _read_counter[0])

        # TEST-09: consecutive gets must return strictly incrementing values
        v1 = ctxt2.get(pv_name)
        v2 = ctxt2.get(pv_name)
        v3 = ctxt2.get(pv_name)

        assert v2 > v1, 'Expected increment on read: v1={}, v2={}'.format(v1, v2)
        assert v3 > v2, 'Expected increment on read: v2={}, v3={}'.format(v2, v3)

        ctxt2.close()


if __name__ == '__main__':
    test_local_root()
    test_increment_on_read()
