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

        # Test UInt64/Int64 (int64In/Out)
        self.add(pr.LocalVariable(
            name     = 'LocalRwInt64',
            value    = 0,
            typeStr  = 'Int64',
            mode     = 'RW'))

        self.add(pr.LocalVariable(
            name     = 'LocalRwUInt64',
            value    = 0,
            typeStr  = 'UInt64',
            mode     = 'RW'))

        # Test String (longStringIn/Out)
        self.add(pr.LocalVariable(
            name     = 'LocalRwString',
            value    = '',
            typeStr  = 'str',
            mode     = 'RW'))

        # Test Bool
        self.add(pr.LocalVariable(
            name     = 'LocalRwBool',
            value    = False,
            typeStr  = 'Bool',
            mode     = 'RW'))

        # Test Enum
        self.add(pr.LocalVariable(
            name     = 'LocalRwEnum',
            value    = 0,
            enum     = {0: 'Off', 1: 'On', 2: 'Auto'},
            mode     = 'RW'))

        # Test explicit integer types
        self.add(pr.LocalVariable(
            name     = 'LocalRwUInt32',
            value    = 0,
            typeStr  = 'UInt32',
            mode     = 'RW'))

        self.add(pr.LocalVariable(
            name     = 'LocalRwInt32',
            value    = 0,
            typeStr  = 'Int32',
            mode     = 'RW'))

        # Test explicit float types
        self.add(pr.LocalVariable(
            name     = 'LocalRwFloat32',
            value    = 0.0,
            typeStr  = 'Float32',
            mode     = 'RW'))

        self.add(pr.LocalVariable(
            name     = 'LocalRwFloat64',
            value    = 0.0,
            typeStr  = 'Float64',
            mode     = 'RW'))

        # Test ndarray
        import numpy as np
        self.add(pr.LocalVariable(
            name     = 'LocalRwArray',
            value    = np.array([1, 2, 3, 4, 5], dtype=np.float64),
            mode     = 'RW'))

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
    def __init__(self, tcp_port=9075):
        pr.Root.__init__(self,
                         name='LocalRoot',
                         description='Local root',
                         timeout=2.0,
                         pollEn=True)

        # Use a memory space emulator
        sim = rogue.interfaces.memory.Emulate(4, 0x1000)
        self.addInterface(sim)

        # Create a memory gateway server
        ms = rogue.interfaces.memory.TcpServer("127.0.0.1", tcp_port)
        self.addInterface(ms)

        # Connect the memory gateways together
        sim << ms

        # Create a memory gateway client
        mc = rogue.interfaces.memory.TcpClient("127.0.0.1", tcp_port, True)
        self.memClient = mc
        self.addInterface(mc)

        # Add SimpleDev
        self.add(SimpleDev(
            name    = 'SimpleDev',
            offset  = 0x0000,
            memBase = mc,
        ))

        # Add CounterDev (both devices share same Root and IOC)
        self.add(DevWithCounter(
            name    = 'CounterDev',
            offset  = 0x1000,
            memBase = mc,
        ))


class LocalRootWithEpics(LocalRoot):
    def __init__(self, use_map=False, tcp_port=9075):
        LocalRoot.__init__(self, tcp_port=tcp_port)

        if use_map:
            # Explicit PV map
            pv_map = {
                'LocalRoot.SimpleDev.LocalRwInt'       : epics_prefix + ':LocalRoot:SimpleDev:LocalRwInt',
                'LocalRoot.SimpleDev.LocalWoInt'       : epics_prefix + ':LocalRoot:SimpleDev:LocalWoInt',
                'LocalRoot.SimpleDev.LocalRwFloat'     : epics_prefix + ':LocalRoot:SimpleDev:LocalRwFloat',
                'LocalRoot.SimpleDev.LocalRwInt64'     : epics_prefix + ':LocalRoot:SimpleDev:LocalRwInt64',
                'LocalRoot.SimpleDev.LocalRwUInt64'    : epics_prefix + ':LocalRoot:SimpleDev:LocalRwUInt64',
                'LocalRoot.SimpleDev.LocalRwString'    : epics_prefix + ':LocalRoot:SimpleDev:LocalRwString',
                'LocalRoot.SimpleDev.LocalRwBool'      : epics_prefix + ':LocalRoot:SimpleDev:LocalRwBool',
                'LocalRoot.SimpleDev.LocalRwEnum'      : epics_prefix + ':LocalRoot:SimpleDev:LocalRwEnum',
                'LocalRoot.SimpleDev.LocalRwUInt32'    : epics_prefix + ':LocalRoot:SimpleDev:LocalRwUInt32',
                'LocalRoot.SimpleDev.LocalRwInt32'     : epics_prefix + ':LocalRoot:SimpleDev:LocalRwInt32',
                'LocalRoot.SimpleDev.LocalRwFloat32'   : epics_prefix + ':LocalRoot:SimpleDev:LocalRwFloat32',
                'LocalRoot.SimpleDev.LocalRwFloat64'   : epics_prefix + ':LocalRoot:SimpleDev:LocalRwFloat64',
                'LocalRoot.SimpleDev.LocalRwArray'     : epics_prefix + ':LocalRoot:SimpleDev:LocalRwArray',
                'LocalRoot.SimpleDev.RemoteRwInt'      : epics_prefix + ':LocalRoot:SimpleDev:RemoteRwInt',
                'LocalRoot.SimpleDev.RemoteWoInt'      : epics_prefix + ':LocalRoot:SimpleDev:RemoteWoInt',
                'LocalRoot.SimpleDev.ResetLocalRwInt'  : epics_prefix + ':LocalRoot:SimpleDev:ResetLocalRwInt',
                'LocalRoot.SimpleDev.SetLocalRwInt'    : epics_prefix + ':LocalRoot:SimpleDev:SetLocalRwInt',
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
    """Test EpicsV7 Server -- put/get round-trips, WO, float, remote, commands"""

    # softioc IOC is a process singleton - can only be initialized once
    print(Context.providers())
    ctxt = Context('pva')

    # Test with autogenerated PV names (pvMap=None)
    with LocalRootWithEpics(use_map=False) as root:
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
            raise AssertionError('pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

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

        # TEST-11: Int64 type (int64In/Out)
        pv_name = device_epics_prefix + ':LocalRwInt64'
        test_value = 9223372036854775807  # max int64
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, test_value)
        test_result = ctxt.get(pv_name)
        if test_result != test_value:
            raise AssertionError('Int64: pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-12: UInt64 type (int64In/Out)
        pv_name = device_epics_prefix + ':LocalRwUInt64'
        test_value = 18446744073709551615  # max uint64
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, test_value)
        test_result = ctxt.get(pv_name)
        if test_result != test_value:
            raise AssertionError('UInt64: pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-13: String type (longStringIn/Out) - test long strings > 40 chars
        pv_name = device_epics_prefix + ':LocalRwString'
        test_value = 'This is a very long string that exceeds the old 40 character limit for EPICS stringIn/Out records'
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, test_value)
        test_result = ctxt.get(pv_name)
        if test_result != test_value:
            raise AssertionError('String: pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-14: Bool type
        pv_name = device_epics_prefix + ':LocalRwBool'
        test_value = 1  # True
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, test_value)
        test_result = ctxt.get(pv_name)
        if test_result != test_value:
            raise AssertionError('Bool: pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-15: Enum type
        pv_name = device_epics_prefix + ':LocalRwEnum'
        test_value = 2  # 'Auto'
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, test_value)
        test_result = ctxt.get(pv_name)
        if test_result != test_value:
            raise AssertionError('Enum: pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-16: UInt32 type
        pv_name = device_epics_prefix + ':LocalRwUInt32'
        test_value = 4294967295  # max uint32
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, test_value)
        test_result = ctxt.get(pv_name)
        if test_result != test_value:
            raise AssertionError('UInt32: pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-17: Int32 type
        pv_name = device_epics_prefix + ':LocalRwInt32'
        test_value = -2147483648  # min int32
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, test_value)
        test_result = ctxt.get(pv_name)
        if test_result != test_value:
            raise AssertionError('Int32: pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-18: Float32 type
        pv_name = device_epics_prefix + ':LocalRwFloat32'
        test_value = 3.14159
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, test_value, transform=lambda value: round(value, 4))
        test_result = round(ctxt.get(pv_name), 4)
        if test_result != round(test_value, 4):
            raise AssertionError('Float32: pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-19: Float64 type
        pv_name = device_epics_prefix + ':LocalRwFloat64'
        test_value = 2.718281828459045
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, test_value, transform=lambda value: round(value, 10))
        test_result = round(ctxt.get(pv_name), 10)
        if test_result != round(test_value, 10):
            raise AssertionError('Float64: pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-20: ndarray type (waveform)
        import numpy as np
        pv_name = device_epics_prefix + ':LocalRwArray'
        test_value = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        ctxt.put(pv_name, test_value)
        time.sleep(0.5)  # Give time for propagation
        test_result = ctxt.get(pv_name)
        if not np.array_equal(test_result, test_value):
            raise AssertionError('Array: pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-21: Increment on read (CounterDev in same Root)
        counter_pv = epics_prefix + ':LocalRoot:CounterDev:IncrOnRead'

        # Wait for PV to become available (TEST-10 coverage)
        wait_pv_value(ctxt, counter_pv, _read_counter[0])

        # TEST-09: consecutive gets must return strictly incrementing values
        v1 = ctxt.get(counter_pv)
        v2 = ctxt.get(counter_pv)
        v3 = ctxt.get(counter_pv)

        if not (v2 > v1):
            raise AssertionError('Expected increment on read: v1={}, v2={}'.format(v1, v2))
        if not (v3 > v2):
            raise AssertionError('Expected increment on read: v2={}, v3={}'.format(v2, v3))

    ctxt.close()


if __name__ == '__main__':
    test_local_root()
