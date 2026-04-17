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

import io
import platform
import re
import sys
import time

import numpy as np
import pytest
import pyrogue as pr
import pyrogue.protocols.epicsV7
import rogue.interfaces.memory

from p4p.client.thread import Context
from pyrogue.protocols.epicsV7 import (
    EpicsConvSeverity,
    EpicsConvStatus,
    _epicsV7_to_pva_type,
    _EPICS_MAX_NAME_LEN,
    _make_epicsV7_suffix,
    _make_shared_pv,
    _PVA_UNSUPPORTED_TYPES,
)

# TODO: p4p cannot discover the softioc/PVXS server on macOS ARM64 because
# macOS does not support UDP broadcast on the loopback interface (lo0).
# Fix the PVA discovery mechanism and remove this skip.
if sys.platform == 'darwin' and platform.machine() == 'arm64':
    pytest.skip('test_epicsV7 skipped on macOS ARM64: softioc/PVXS PVA '
                'discovery does not work over loopback on this platform',
                allow_module_level=True)

epics_prefix = 'test_ioc_v7'
PV_DISCOVERY_TIMEOUT = 10.0
PropagateTimeout = 5.0
POLL_INTERVAL = 0.05
_local_ro_int = [0]  # backing storage for LocalRoInt (mode='RO') poll test


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
            name     = 'LocalRwUInt8',
            value    = 0,
            typeStr  = 'UInt8',
            mode     = 'RW'))

        self.add(pr.LocalVariable(
            name     = 'LocalRwUInt16',
            value    = 0,
            typeStr  = 'UInt16',
            mode     = 'RW'))

        self.add(pr.LocalVariable(
            name     = 'LocalRwUInt32',
            value    = 0,
            typeStr  = 'UInt32',
            mode     = 'RW'))

        self.add(pr.LocalVariable(
            name     = 'LocalRwInt8',
            value    = 0,
            typeStr  = 'Int8',
            mode     = 'RW'))

        self.add(pr.LocalVariable(
            name     = 'LocalRwInt16',
            value    = 0,
            typeStr  = 'Int16',
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

        # Test mode='RO' (longIn); localGet backed by _local_ro_int so the test
        # can control the value without needing to bypass mode restrictions.
        self.add(pr.LocalVariable(
            name         = 'LocalRoInt',
            value        = 0,
            mode         = 'RO',
            localGet     = lambda dev, var: _local_ro_int[0],
            pollInterval = 0.5,
        ))

        # Test list nativeType (longStringIn/Out)
        self.add(pr.LocalVariable(
            name  = 'LocalRwList',
            value = [1, 2, 3],
            mode  = 'RW'))

        # Test dict nativeType (longStringIn/Out)
        self.add(pr.LocalVariable(
            name  = 'LocalRwDict',
            value = {'a': 1, 'b': 2},
            mode  = 'RW'))


class LongNameSubDev(pr.Device):
    """Device with variable names that exceed the 60-char EPICS CA limit when
    combined with the base prefix, to test transparent PV name hashing."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # This variable's full PV name will be:
        # test_ioc_v7:LocalRoot:LongNameSubDev:ThisIsAVeryLongVariableNameThatExceedsSixtyCharacterLimit
        # Which is well over 60 chars, triggering the hash path.
        self.add(pr.LocalVariable(
            name  = 'ThisIsAVeryLongVariableNameThatExceedsSixtyCharacterLimit',
            value = 0,
            mode  = 'RW'))

        # A second long-named variable to verify both get hashed independently
        self.add(pr.LocalVariable(
            name  = 'AnotherExtremelyLongVariableNameForTestingHashBehavior',
            value = 3.14,
            mode  = 'RW'))

        # A short-named variable in the same device to verify it is NOT hashed
        self.add(pr.LocalVariable(
            name  = 'ShortVar',
            value = 42,
            mode  = 'RW'))

        # Long-named Bool variable to exercise the '?' SharedPV type on the PVA alias path
        self.add(pr.LocalVariable(
            name    = 'ThisIsAVeryLongBoolVariableNameForTestingBoolPvaType',
            value   = False,
            typeStr = 'Bool',
            mode    = 'RW'))

        # Long-named UInt32 variable to exercise the 'I' SharedPV type on the PVA alias path
        self.add(pr.LocalVariable(
            name    = 'ThisIsAVeryLongUInt32VariableNameThatExceedsSixtyCharLimit',
            value   = 0,
            typeStr = 'UInt32',
            mode    = 'RW'))

        # Float64 variable with units and alarm thresholds for alarm metadata tests (PVA-06).
        # Full PV name: test_ioc_v7:LocalRoot:LongNameSubDev:AlarmTestFloatWithUnitsAndThresholds
        # = 74 chars > 60 → gets hashed CA name and a PVA long-name alias.
        self.add(pr.LocalVariable(
            name        = 'AlarmTestFloatWithUnitsAndThresholds',
            value       = 0.0,
            typeStr     = 'Float64',
            mode        = 'RW',
            units       = 'volts',
            minimum     = 0.0,
            maximum     = 10.0,
            lowAlarm    = 1.0,
            lowWarning  = 2.0,
            highWarning = 8.0,
            highAlarm   = 9.0,
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

        # Add LongNameSubDev for long PV name hashing tests
        self.add(LongNameSubDev(
            name    = 'LongNameSubDev',
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
                'LocalRoot.SimpleDev.LocalRwUInt8'     : epics_prefix + ':LocalRoot:SimpleDev:LocalRwUInt8',
                'LocalRoot.SimpleDev.LocalRwUInt16'    : epics_prefix + ':LocalRoot:SimpleDev:LocalRwUInt16',
                'LocalRoot.SimpleDev.LocalRwUInt32'    : epics_prefix + ':LocalRoot:SimpleDev:LocalRwUInt32',
                'LocalRoot.SimpleDev.LocalRwInt8'      : epics_prefix + ':LocalRoot:SimpleDev:LocalRwInt8',
                'LocalRoot.SimpleDev.LocalRwInt16'     : epics_prefix + ':LocalRoot:SimpleDev:LocalRwInt16',
                'LocalRoot.SimpleDev.LocalRwInt32'     : epics_prefix + ':LocalRoot:SimpleDev:LocalRwInt32',
                'LocalRoot.SimpleDev.LocalRwFloat32'   : epics_prefix + ':LocalRoot:SimpleDev:LocalRwFloat32',
                'LocalRoot.SimpleDev.LocalRwFloat64'   : epics_prefix + ':LocalRoot:SimpleDev:LocalRwFloat64',
                'LocalRoot.SimpleDev.LocalRwArray'     : epics_prefix + ':LocalRoot:SimpleDev:LocalRwArray',
                'LocalRoot.SimpleDev.RemoteRwInt'      : epics_prefix + ':LocalRoot:SimpleDev:RemoteRwInt',
                'LocalRoot.SimpleDev.RemoteWoInt'      : epics_prefix + ':LocalRoot:SimpleDev:RemoteWoInt',
                'LocalRoot.SimpleDev.LocalRoInt'       : epics_prefix + ':LocalRoot:SimpleDev:LocalRoInt',
                'LocalRoot.SimpleDev.ResetLocalRwInt'  : epics_prefix + ':LocalRoot:SimpleDev:ResetLocalRwInt',
                'LocalRoot.SimpleDev.SetLocalRwInt'    : epics_prefix + ':LocalRoot:SimpleDev:SetLocalRwInt',
                'LocalRoot.SimpleDev.LocalRwList'      : epics_prefix + ':LocalRoot:SimpleDev:LocalRwList',
                'LocalRoot.SimpleDev.LocalRwDict'      : epics_prefix + ':LocalRoot:SimpleDev:LocalRwDict',
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


# TEST-01: convergence helper
def wait_pv_value(ctxt, pv_name, expected, timeout=PropagateTimeout, transform=None):
    start = time.monotonic()

    while True:
        try:
            value = ctxt.get(pv_name)
            if transform is not None:
                value = transform(value)
            if value == expected:
                return
        except Exception:
            pass

        if (time.monotonic() - start) > timeout:
            raise AssertionError('Timed out waiting for pv_name={} expected={} last={}'.format(
                pv_name,
                expected,
                value if 'value' in locals() else 'unavailable'))

        time.sleep(POLL_INTERVAL)


def test_pv_name_hash():
    """Unit tests for _make_epicsV7_suffix and _EPICS_MAX_NAME_LEN -- no IOC required."""
    assert _EPICS_MAX_NAME_LEN == 60

    # Short name unchanged
    assert _make_epicsV7_suffix('TestBase', 'Short') == 'Short'

    # Exactly 60 chars unchanged (10 + 1 + 49 = 60)
    base = 'B' * 10
    suffix = 'S' * 49
    assert len(base + ':' + suffix) == 60
    assert _make_epicsV7_suffix(base, suffix) == suffix

    # 61 chars triggers hash (10 + 1 + 50 = 61)
    suffix61 = 'S' * 50
    result = _make_epicsV7_suffix(base, suffix61)
    assert result != suffix61
    assert re.match(r'^tail_[0-9a-f]{10}$', result)

    # Deterministic
    long_suffix = 'LongSuffix' + 'A' * 50
    r1 = _make_epicsV7_suffix('TestBase', long_suffix)
    assert r1 == _make_epicsV7_suffix('TestBase', long_suffix)

    # Different inputs produce different hashes
    assert _make_epicsV7_suffix('TestBase', 'LongSuffix' + 'A' * 50) != \
           _make_epicsV7_suffix('TestBase', 'LongSuffix' + 'B' * 50)

    # Hash uses full name (different base → different hash for same suffix)
    long_s = 'SameSuffix' + 'Z' * 50
    assert _make_epicsV7_suffix('Base1' + 'X' * 20, long_s) != \
           _make_epicsV7_suffix('Base2' + 'X' * 20, long_s)


def test_pva_type_mapping():
    """Unit tests for _epicsV7_to_pva_type -- verifies all p4p type characters."""
    class FakeVar:
        def __init__(self, typeStr=None, nativeType=None, disp=None, enum=None):
            self.typeStr   = typeStr
            self.nativeType = nativeType
            self.disp      = disp
            self.enum      = enum or {}

    # Bool → '?' (not 'i')
    assert _epicsV7_to_pva_type(FakeVar(typeStr='Bool')) == '?'

    # Unsigned 64-bit → 'L'; signed 64-bit → 'l'
    assert _epicsV7_to_pva_type(FakeVar(typeStr='UInt64')) == 'L'
    assert _epicsV7_to_pva_type(FakeVar(typeStr='Int64')) == 'l'

    # Unsigned ints get distinct unsigned type characters
    assert _epicsV7_to_pva_type(FakeVar(typeStr='UInt32')) == 'I'
    assert _epicsV7_to_pva_type(FakeVar(typeStr='UInt16')) == 'H'
    assert _epicsV7_to_pva_type(FakeVar(typeStr='UInt8')) == 'B'

    # Signed ints get distinct signed type characters
    assert _epicsV7_to_pva_type(FakeVar(typeStr='Int32')) == 'i'
    assert _epicsV7_to_pva_type(FakeVar(typeStr='int')) == 'i'
    assert _epicsV7_to_pva_type(FakeVar(typeStr='Int16')) == 'h'
    assert _epicsV7_to_pva_type(FakeVar(typeStr='Int8')) == 'b'

    # Float types
    assert _epicsV7_to_pva_type(FakeVar(typeStr='Float32')) == 'f'
    assert _epicsV7_to_pva_type(FakeVar(typeStr='Float64')) == 'd'
    assert _epicsV7_to_pva_type(FakeVar(typeStr='Double64')) == 'd'
    assert _epicsV7_to_pva_type(FakeVar(typeStr='float')) == 'd'

    # String / collection types → 's'
    assert _epicsV7_to_pva_type(FakeVar(typeStr='str')) == 's'
    assert _epicsV7_to_pva_type(FakeVar(typeStr='NoneType')) == 's'
    assert _epicsV7_to_pva_type(FakeVar(typeStr='')) == 's'
    assert _epicsV7_to_pva_type(FakeVar(nativeType=list, typeStr='list')) == 's'
    assert _epicsV7_to_pva_type(FakeVar(nativeType=dict, typeStr='dict')) == 's'

    # ndarray → 'ndarray'
    assert _epicsV7_to_pva_type(FakeVar(nativeType=np.ndarray)) == 'ndarray'

    # Enum: ≤16 choices → 'enum'; >16 → 's'
    assert _epicsV7_to_pva_type(FakeVar(disp='enum', enum={i: str(i) for i in range(3)})) == 'enum'
    assert _epicsV7_to_pva_type(FakeVar(disp='enum', enum={i: str(i) for i in range(17)})) == 's'

    # Structural types are rejected by _make_shared_pv
    assert _PVA_UNSUPPORTED_TYPES == frozenset(('v', 'U', 'S'))
    for bad_type in _PVA_UNSUPPORTED_TYPES:
        try:
            _make_shared_pv(FakeVar(typeStr='int'), bad_type, None)
            raise AssertionError(f"Expected ValueError for structural type '{bad_type}'")
        except ValueError:
            pass


def test_epics_conv_status_severity():
    """Unit tests for EpicsConvStatus and EpicsConvSeverity -- no IOC required."""

    class FakeVal:
        def __init__(self, status='None', severity='None'):
            self.status   = status
            self.severity = severity

    # EpicsConvStatus: all named alarm states map to their EPICS alarm status codes
    assert EpicsConvStatus(FakeVal(status='AlarmLoLo'))  == 5  # epicsAlarmLoLo
    assert EpicsConvStatus(FakeVal(status='AlarmLow'))   == 6  # epicsAlarmLow
    assert EpicsConvStatus(FakeVal(status='AlarmHiHi'))  == 3  # epicsAlarmHiHi
    assert EpicsConvStatus(FakeVal(status='AlarmHigh'))  == 4  # epicsAlarmHigh
    assert EpicsConvStatus(FakeVal(status='None'))       == 0  # no alarm
    assert EpicsConvStatus(FakeVal(status='Good'))       == 0  # no alarm
    assert EpicsConvStatus(FakeVal(status=''))           == 0  # no alarm

    # EpicsConvSeverity: maps severity strings to EPICS severity codes
    assert EpicsConvSeverity(FakeVal(severity='AlarmMinor')) == 1  # epicsSevMinor
    assert EpicsConvSeverity(FakeVal(severity='AlarmMajor')) == 2  # epicsSevMajor
    assert EpicsConvSeverity(FakeVal(severity='None'))       == 0  # no alarm
    assert EpicsConvSeverity(FakeVal(severity='Good'))       == 0  # no alarm
    assert EpicsConvSeverity(FakeVal(severity=''))           == 0  # no alarm


def test_make_shared_pv_alarm_display():
    """Unit test: _make_shared_pv sets alarm and display metadata on the SharedPV initial value.

    Verifies alarm.severity, alarm.status, display.units, display.limits, and
    valueAlarm threshold fields without requiring a running IOC.
    """

    class FakeVarVal:
        value     = 0.0
        valueDisp = '0.0'
        severity  = 'AlarmMinor'
        status    = 'AlarmHigh'

    class FakeVar:
        typeStr     = 'Float64'
        nativeType  = float
        disp        = None
        enum        = {}
        description = 'Test variable'
        units       = 'volts'
        minimum     = 0.0
        maximum     = 10.0
        lowAlarm    = 1.0
        lowWarning  = 2.0
        highWarning = 8.0
        highAlarm   = 9.0

        def getVariableValue(self, read=False):
            return FakeVarVal()

    pv  = _make_shared_pv(FakeVar(), 'd', None)
    curr = pv.current()
    # SharedPV.current() returns the NType-wrapped form; .raw is the underlying Value
    raw = curr.raw if hasattr(curr, 'raw') else curr

    # Alarm fields populated from FakeVarVal.severity / .status
    assert raw.alarm.severity == 1, \
        'Expected severity=1 (AlarmMinor), got {}'.format(raw.alarm.severity)
    assert raw.alarm.status == 4, \
        'Expected status=4 (AlarmHigh), got {}'.format(raw.alarm.status)

    # Display metadata
    assert raw.display.units       == 'volts',         'Expected units=volts'
    assert raw.display.description == 'Test variable', 'Expected description'
    assert raw.display.limitHigh   == 10.0,            'Expected limitHigh=10.0'
    assert raw.display.limitLow    == 0.0,             'Expected limitLow=0.0'

    # Alarm threshold fields
    assert raw.valueAlarm.highAlarmLimit   == 9.0, 'Expected highAlarmLimit=9.0'
    assert raw.valueAlarm.highWarningLimit == 8.0, 'Expected highWarningLimit=8.0'
    assert raw.valueAlarm.lowWarningLimit  == 2.0, 'Expected lowWarningLimit=2.0'
    assert raw.valueAlarm.lowAlarmLimit    == 1.0, 'Expected lowAlarmLimit=1.0'


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

        # TEST-02: Wait for PVs to become visible through the EPICS server (TEST-01 coverage)
        wait_pv_value(ctxt, device_epics_prefix + ':LocalRwInt', 0, timeout=PV_DISCOVERY_TIMEOUT)

        # TEST-03: RW a variable holding a scalar int value
        pv_name = device_epics_prefix + ':LocalRwInt'
        test_value = 314
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, test_value)  # TEST-01 coverage
        test_result = ctxt.get(pv_name)
        if test_result != test_value:
            raise AssertionError('pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-04: WO a variable holding a scalar int value
        pv_name = device_epics_prefix + ':LocalWoInt'
        test_value = 314
        ctxt.put(pv_name, test_value)

        # TEST-05: RW a variable holding a float value
        pv_name = device_epics_prefix + ':LocalRwFloat'
        test_value = 5.67
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, test_value, transform=lambda value: round(value, 2))  # TEST-01 coverage
        test_result = round(ctxt.get(pv_name), 2)
        if test_result != test_value:
            raise AssertionError('pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-06: RW a remote variable holding a scalar int value
        pv_name = device_epics_prefix + ':RemoteRwInt'
        test_value = 314
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, test_value)  # TEST-01 coverage
        test_result = ctxt.get(pv_name)
        if test_result != test_value:
            raise AssertionError('pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-07: WO a remote variable holding a scalar int value
        pv_name = device_epics_prefix + ':RemoteWoInt'
        test_value = 314
        ctxt.put(pv_name, test_value)

        # TEST-08: Commands invoked via caput (ctxt.put), NOT ctxt.rpc()
        # No-arg command: set LocalRwInt non-zero, then reset via caput with value=0
        pv_name = device_epics_prefix + ':LocalRwInt'
        reset_pv = device_epics_prefix + ':ResetLocalRwInt'
        test_value = 42
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, test_value)  # TEST-01 coverage
        ctxt.put(reset_pv, 0)  # value=0 triggers no-arg command call
        wait_pv_value(ctxt, pv_name, 0)  # TEST-01 coverage
        test_result = ctxt.get(pv_name)
        if test_result != 0:
            raise AssertionError('Command reset failed: pv_name={}: expected=0; test_result={}'.format(
                pv_name, test_result))

        # TEST-09 (with-arg): caput with non-zero value sets LocalRwInt to that value
        set_pv = device_epics_prefix + ':SetLocalRwInt'
        test_value = 99
        ctxt.put(set_pv, test_value)
        wait_pv_value(ctxt, pv_name, test_value)  # TEST-01 coverage
        test_result = ctxt.get(pv_name)
        if test_result != test_value:
            raise AssertionError('Command set failed: pv_name={}: expected={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-10: Int64 type (int64In/Out)
        pv_name = device_epics_prefix + ':LocalRwInt64'
        test_value = 9223372036854775807  # max int64
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, test_value)
        test_result = ctxt.get(pv_name)
        if test_result != test_value:
            raise AssertionError('Int64: pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-11: UInt64 type (int64In/Out for CA; p4p type 'L' for PVA long-name alias)
        # softioc still uses signed int64Out, so test within signed int64 range.
        pv_name = device_epics_prefix + ':LocalRwUInt64'
        test_value = 9223372036854775806  # INT64_MAX - 1, fits in int64Out without overflow
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, test_value)
        test_result = ctxt.get(pv_name)
        if test_result != test_value:
            raise AssertionError('UInt64: pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-12: String type (longStringIn/Out) - test long strings > 40 chars
        pv_name = device_epics_prefix + ':LocalRwString'
        test_value = 'This is a very long string that exceeds the old 40 character limit for EPICS stringIn/Out records'
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, test_value)
        test_result = ctxt.get(pv_name)
        if test_result != test_value:
            raise AssertionError('String: pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-13: Bool type (softioc longIn/Out; p4p type '?' for PVA long-name alias)
        # softioc uses longOut so ctxt.get returns int; test True/False as int 1/0.
        pv_name = device_epics_prefix + ':LocalRwBool'
        for test_value in (1, 0):
            ctxt.put(pv_name, test_value)
            wait_pv_value(ctxt, pv_name, test_value)
            test_result = ctxt.get(pv_name)
            if test_result != test_value:
                raise AssertionError('Bool: pv_name={}: test_value={}; test_result={}'.format(
                    pv_name, test_value, test_result))

        # TEST-14: Enum type
        pv_name = device_epics_prefix + ':LocalRwEnum'
        test_value = 2  # 'Auto'
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, test_value)
        test_result = ctxt.get(pv_name)
        if test_result != test_value:
            raise AssertionError('Enum: pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-15: UInt32 type (softioc longIn/Out; p4p type 'I' for PVA long-name alias)
        # softioc uses signed longOut, so test within signed int32 range.
        pv_name = device_epics_prefix + ':LocalRwUInt32'
        test_value = 2147483647  # INT32_MAX, fits in longOut without overflow
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, test_value)
        test_result = ctxt.get(pv_name)
        if test_result != test_value:
            raise AssertionError('UInt32: pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-16: Int32 type
        pv_name = device_epics_prefix + ':LocalRwInt32'
        test_value = -2147483648  # min int32
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, test_value)
        test_result = ctxt.get(pv_name)
        if test_result != test_value:
            raise AssertionError('Int32: pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-17: UInt8 type (p4p type 'B')
        pv_name = device_epics_prefix + ':LocalRwUInt8'
        test_value = 255  # max uint8
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, test_value)
        test_result = ctxt.get(pv_name)
        if test_result != test_value:
            raise AssertionError('UInt8: pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-18: UInt16 type (p4p type 'H')
        pv_name = device_epics_prefix + ':LocalRwUInt16'
        test_value = 65535  # max uint16
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, test_value)
        test_result = ctxt.get(pv_name)
        if test_result != test_value:
            raise AssertionError('UInt16: pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-19: Int8 type (p4p type 'b')
        pv_name = device_epics_prefix + ':LocalRwInt8'
        test_value = -128  # min int8
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, test_value)
        test_result = ctxt.get(pv_name)
        if test_result != test_value:
            raise AssertionError('Int8: pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-20: Int16 type (p4p type 'h')
        pv_name = device_epics_prefix + ':LocalRwInt16'
        test_value = -32768  # min int16
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, test_value)
        test_result = ctxt.get(pv_name)
        if test_result != test_value:
            raise AssertionError('Int16: pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-21: Float32 type
        pv_name = device_epics_prefix + ':LocalRwFloat32'
        test_value = 3.14159
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, round(test_value, 4), transform=lambda value: round(value, 4))
        test_result = round(ctxt.get(pv_name), 4)
        if test_result != round(test_value, 4):
            raise AssertionError('Float32: pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-22: Float64 type
        pv_name = device_epics_prefix + ':LocalRwFloat64'
        test_value = 2.718281828459045
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, round(test_value, 10), transform=lambda value: round(value, 10))
        test_result = round(ctxt.get(pv_name), 10)
        if test_result != round(test_value, 10):
            raise AssertionError('Float64: pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-23: ndarray type (waveform)
        pv_name = device_epics_prefix + ':LocalRwArray'
        test_value = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        ctxt.put(pv_name, test_value)
        wait_pv_value(
            ctxt,
            pv_name,
            tuple(test_value.tolist()),
            transform=lambda value: tuple(value.tolist()),
        )
        test_result = ctxt.get(pv_name)
        if not np.array_equal(test_result, test_value):
            raise AssertionError('Array: pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-24: list nativeType (longStringIn/Out) — verify PV is accessible
        pv_name = device_epics_prefix + ':LocalRwList'
        wait_pv_value(ctxt, pv_name, True, transform=lambda v: isinstance(v, str) and len(v) > 0)

        # TEST-25: dict nativeType (longStringIn/Out) — verify PV is accessible
        pv_name = device_epics_prefix + ':LocalRwDict'
        wait_pv_value(ctxt, pv_name, True, transform=lambda v: isinstance(v, str) and len(v) > 0)

        # TEST-26: RO LocalVariable (longIn) — verifies _varUpdated works for In records.
        # ProcessDeviceSupportIn.set() has NO process= parameter; passing process=True raises
        # TypeError (silently swallowed), leaving the record stuck at 0.
        # Control the value via _local_ro_int; wait for the 0.5 s poll to fire and
        # update the EPICS longIn record, then verify PVA GET returns the new value.
        ro_pv = device_epics_prefix + ':LocalRoInt'
        test_value = 99
        _local_ro_int[0] = test_value
        wait_pv_value(ctxt, ro_pv, test_value)
        test_result = ctxt.get(ro_pv)
        if test_result != test_value:
            raise AssertionError('RO In record not updated: pv_name={}: expected={}; got={}'.format(
                ro_pv, test_value, test_result))

        # ---- Long PV name hashing tests (HASH-05, OPS-01, OPS-02) ----

        # Verify the long-named PVs are accessible via PVA using hashed CA names.
        # The suffix is hashed to tail_XXXXXXXXXX when base:suffix > 60 chars.
        long_var_name_1 = 'ThisIsAVeryLongVariableNameThatExceedsSixtyCharacterLimit'
        long_suffix_1 = 'LocalRoot:LongNameSubDev:' + long_var_name_1
        hashed_suffix_1 = _make_epicsV7_suffix(epics_prefix, long_suffix_1)
        hashed_pv_1 = epics_prefix + ':' + hashed_suffix_1

        long_var_name_2 = 'AnotherExtremelyLongVariableNameForTestingHashBehavior'
        long_suffix_2 = 'LocalRoot:LongNameSubDev:' + long_var_name_2
        hashed_suffix_2 = _make_epicsV7_suffix(epics_prefix, long_suffix_2)
        hashed_pv_2 = epics_prefix + ':' + hashed_suffix_2

        short_pv = epics_prefix + ':LocalRoot:LongNameSubDev:ShortVar'

        # TEST-27: Verify hashed PVs are reachable (HASH-05)
        # The hashed suffix should start with 'tail_' since the full name exceeds 60 chars
        assert hashed_suffix_1.startswith('tail_'), \
            'Expected hashed suffix for long var 1, got: {}'.format(hashed_suffix_1)
        assert hashed_suffix_2.startswith('tail_'), \
            'Expected hashed suffix for long var 2, got: {}'.format(hashed_suffix_2)

        # Verify PVs are accessible via the hashed CA names
        wait_pv_value(ctxt, hashed_pv_1, 0)
        wait_pv_value(ctxt, hashed_pv_2, True,
                      transform=lambda v: abs(v - 3.14) < 0.01)

        # TEST-28: RW round-trip on a hashed PV (HASH-05)
        test_value = 777
        ctxt.put(hashed_pv_1, test_value)
        wait_pv_value(ctxt, hashed_pv_1, test_value)
        test_result = ctxt.get(hashed_pv_1)
        if test_result != test_value:
            raise AssertionError(
                'Long-name PV RW failed: pv_name={}: expected={}; got={}'.format(
                    hashed_pv_1, test_value, test_result))

        # TEST-29: Short-named PV in same device is NOT hashed (zero regression)
        wait_pv_value(ctxt, short_pv, 42)
        test_value = 99
        ctxt.put(short_pv, test_value)
        wait_pv_value(ctxt, short_pv, test_value)
        test_result = ctxt.get(short_pv)
        if test_result != test_value:
            raise AssertionError(
                'Short-name PV in LongNameSubDev failed: expected={}; got={}'.format(
                    test_value, test_result))

        # TEST-30: list() returns full long names, not hashed names (OPS-01)
        pv_map = root.epics.list()
        long_path_1 = 'LocalRoot.LongNameSubDev.' + long_var_name_1
        full_long_name_1 = epics_prefix + ':' + long_suffix_1
        assert long_path_1 in pv_map, \
            'list() missing long-named PV path: {}'.format(long_path_1)
        assert pv_map[long_path_1] == full_long_name_1, \
            'list() should show full long name, got: {}'.format(pv_map[long_path_1])

        # TEST-31: dump() shows annotation for hashed PVs (OPS-02)
        dump_output = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = dump_output
        root.epics.dump()
        sys.stdout = old_stdout
        dump_text = dump_output.getvalue()

        # Verify dump contains the full long name
        assert full_long_name_1 in dump_text, \
            'dump() should contain full long name: {}'.format(full_long_name_1)
        # Verify dump contains the CA annotation for the hashed PV
        assert '(CA: ' + hashed_pv_1 + ')' in dump_text, \
            'dump() should annotate hashed PV with CA name: {}'.format(hashed_pv_1)

        # TEST-32: Verify all existing short-named PVs still work (zero regression)
        # Re-verify a basic RW round-trip on a standard PV
        std_pv = epics_prefix + ':LocalRoot:SimpleDev:LocalRwInt'
        test_value = 12345
        ctxt.put(std_pv, test_value)
        wait_pv_value(ctxt, std_pv, test_value)
        test_result = ctxt.get(std_pv)
        if test_result != test_value:
            raise AssertionError(
                'Zero-regression check failed on standard PV: expected={}; got={}'.format(
                    test_value, test_result))

        # ---- PVA long-name alias tests (PVA-01 through PVA-05) ----

        # Compute full long PVA names for the hashed PVs
        long_pv_full_1 = epics_prefix + ':' + long_suffix_1
        long_pv_full_2 = epics_prefix + ':' + long_suffix_2

        # TEST-33: pvget on full long name returns current value (PVA-01, PVA-05)
        # The hashed PV was left at test_value=777 from TEST-28 above
        wait_pv_value(ctxt, long_pv_full_1, 777)

        # TEST-34: pvput via full long name, read back via long name (PVA-02)
        test_value = 888
        ctxt.put(long_pv_full_1, test_value)
        wait_pv_value(ctxt, long_pv_full_1, test_value)
        test_result = ctxt.get(long_pv_full_1)
        if test_result != test_value:
            raise AssertionError(
                'PVA long-name put/get failed: pv={}: expected={}; got={}'.format(
                    long_pv_full_1, test_value, test_result))

        # TEST-35: PVA write via long name visible on hashed CA name (PVA-03 fan-out)
        test_value = 555
        ctxt.put(long_pv_full_1, test_value)
        wait_pv_value(ctxt, hashed_pv_1, test_value)
        test_result = ctxt.get(hashed_pv_1)
        if test_result != test_value:
            raise AssertionError(
                'PVA->CA fan-out failed: long={} CA={}: expected={}; got={}'.format(
                    long_pv_full_1, hashed_pv_1, test_value, test_result))

        # TEST-36: CA write via short name visible on full long name (PVA-03 reverse fan-out)
        test_value = 444
        ctxt.put(hashed_pv_1, test_value)
        wait_pv_value(ctxt, long_pv_full_1, test_value)
        test_result = ctxt.get(long_pv_full_1)
        if test_result != test_value:
            raise AssertionError(
                'CA->PVA fan-out failed: CA={} long={}: expected={}; got={}'.format(
                    hashed_pv_1, long_pv_full_1, test_value, test_result))

        # TEST-37: Second hashed PV (float) accessible via full long name (PVA-01)
        wait_pv_value(ctxt, long_pv_full_2, True,
                      transform=lambda v: isinstance(v, float))
        test_value = 2.718
        ctxt.put(long_pv_full_2, test_value)
        wait_pv_value(ctxt, long_pv_full_2, round(test_value, 3),
                      transform=lambda v: round(v, 3))

        # TEST-38: Short-named PVs unaffected by PVA alias layer (zero regression)
        std_pv = epics_prefix + ':LocalRoot:SimpleDev:LocalRwInt'
        test_value = 54321
        ctxt.put(std_pv, test_value)
        wait_pv_value(ctxt, std_pv, test_value)
        test_result = ctxt.get(std_pv)
        if test_result != test_value:
            raise AssertionError(
                'Zero-regression after PVA alias layer: expected={}; got={}'.format(
                    test_value, test_result))

        # ---- New type SharedPV tests (Bool '?', UInt32 'I') ----

        # TEST-39: Bool variable via PVA long-name alias (SharedPV type '?')
        # Verify the SharedPV is created and the full long name is accessible.
        long_bool_var = 'ThisIsAVeryLongBoolVariableNameForTestingBoolPvaType'
        long_bool_suffix = 'LocalRoot:LongNameSubDev:' + long_bool_var
        long_bool_pv = epics_prefix + ':' + long_bool_suffix
        hashed_bool_suffix = _make_epicsV7_suffix(epics_prefix, long_bool_suffix)
        assert hashed_bool_suffix.startswith('tail_'), \
            'Expected hash for Bool long var, got: {}'.format(hashed_bool_suffix)

        # Write True via full long PVA name; read back and verify
        ctxt.put(long_bool_pv, True)
        wait_pv_value(ctxt, long_bool_pv, True, transform=lambda v: bool(v))
        ctxt.put(long_bool_pv, False)
        wait_pv_value(ctxt, long_bool_pv, False, transform=lambda v: bool(v))

        # TEST-40: UInt32 variable via PVA long-name alias (SharedPV type 'I')
        # Verify the SharedPV is created and the full long name is accessible.
        long_u32_var = 'ThisIsAVeryLongUInt32VariableNameThatExceedsSixtyCharLimit'
        long_u32_suffix = 'LocalRoot:LongNameSubDev:' + long_u32_var
        long_u32_pv = epics_prefix + ':' + long_u32_suffix
        hashed_u32_suffix = _make_epicsV7_suffix(epics_prefix, long_u32_suffix)
        assert hashed_u32_suffix.startswith('tail_'), \
            'Expected hash for UInt32 long var, got: {}'.format(hashed_u32_suffix)

        # Write a value within int32 range (softioc longOut limitation) and verify round-trip
        test_value = 12345678
        ctxt.put(long_u32_pv, test_value)
        wait_pv_value(ctxt, long_u32_pv, test_value)
        test_result = ctxt.get(long_u32_pv)
        if test_result != test_value:
            raise AssertionError(
                'UInt32 PVA long-name: expected={}; got={}'.format(test_value, test_result))

        # ---- Alarm and display metadata on PVA long-name aliases (PVA-06) ----

        # The alarm test variable is long enough to be hashed and get a PVA alias:
        # test_ioc_v7:LocalRoot:LongNameSubDev:AlarmTestFloatWithUnitsAndThresholds = 74 chars
        alarm_var_name   = 'AlarmTestFloatWithUnitsAndThresholds'
        alarm_suffix     = 'LocalRoot:LongNameSubDev:' + alarm_var_name
        alarm_long_pv    = epics_prefix + ':' + alarm_suffix
        alarm_hashed_sfx = _make_epicsV7_suffix(epics_prefix, alarm_suffix)
        assert alarm_hashed_sfx.startswith('tail_'), \
            'Expected hashed suffix for alarm test var, got: {}'.format(alarm_hashed_sfx)

        # Use a raw Context (unwraps={}) so ctxt_raw.get() returns the full p4p Value
        # with alarm, display, and valueAlarm fields rather than the unwrapped scalar.
        ctxt_raw = Context('pva', unwrap={})

        # Reset variable to 0.0 (no alarm) and wait for the hashed CA PV to stabilise
        root.LongNameSubDev.AlarmTestFloatWithUnitsAndThresholds.set(0.0)
        alarm_hashed_pv = epics_prefix + ':' + alarm_hashed_sfx
        wait_pv_value(ctxt, alarm_hashed_pv, 0.0, transform=lambda v: round(v, 1))

        # TEST-41: Initial PVA value carries display metadata (units and limits)
        raw_val = ctxt_raw.get(alarm_long_pv)
        assert raw_val.display.units    == 'volts', \
            'Expected display.units=volts, got: {}'.format(raw_val.display.units)
        assert raw_val.display.limitHigh == 10.0, \
            'Expected display.limitHigh=10.0, got: {}'.format(raw_val.display.limitHigh)
        assert raw_val.display.limitLow  == 0.0, \
            'Expected display.limitLow=0.0, got: {}'.format(raw_val.display.limitLow)

        # TEST-42: Value within normal range → no alarm (severity=0, status=0)
        root.LongNameSubDev.AlarmTestFloatWithUnitsAndThresholds.set(5.0)
        wait_pv_value(
            ctxt_raw,
            alarm_long_pv,
            (0, 0),
            transform=lambda value: (value.alarm.severity, value.alarm.status),
        )
        raw_val = ctxt_raw.get(alarm_long_pv)
        assert raw_val.alarm.severity == 0, \
            'Expected severity=0 for value=5.0, got: {}'.format(raw_val.alarm.severity)
        assert raw_val.alarm.status == 0, \
            'Expected status=0 for value=5.0, got: {}'.format(raw_val.alarm.status)

        # TEST-43: Value above highAlarm → major alarm (severity=2, status=3 AlarmHiHi)
        root.LongNameSubDev.AlarmTestFloatWithUnitsAndThresholds.set(9.5)
        wait_pv_value(
            ctxt_raw,
            alarm_long_pv,
            (2, 3),
            transform=lambda value: (value.alarm.severity, value.alarm.status),
        )
        raw_val = ctxt_raw.get(alarm_long_pv)
        assert raw_val.alarm.severity == 2, \
            'Expected severity=2 (major) for value=9.5 > highAlarm=9.0, got: {}'.format(
                raw_val.alarm.severity)
        assert raw_val.alarm.status == 3, \
            'Expected status=3 (AlarmHiHi) for value=9.5, got: {}'.format(raw_val.alarm.status)

        # TEST-44: Value below lowAlarm → major alarm (severity=2, status=5 AlarmLoLo)
        root.LongNameSubDev.AlarmTestFloatWithUnitsAndThresholds.set(0.5)
        wait_pv_value(
            ctxt_raw,
            alarm_long_pv,
            (2, 5),
            transform=lambda value: (value.alarm.severity, value.alarm.status),
        )
        raw_val = ctxt_raw.get(alarm_long_pv)
        assert raw_val.alarm.severity == 2, \
            'Expected severity=2 (major) for value=0.5 < lowAlarm=1.0, got: {}'.format(
                raw_val.alarm.severity)
        assert raw_val.alarm.status == 5, \
            'Expected status=5 (AlarmLoLo) for value=0.5, got: {}'.format(raw_val.alarm.status)

        # TEST-45: Value between lowAlarm and lowWarning → minor alarm (severity=1, status=6)
        root.LongNameSubDev.AlarmTestFloatWithUnitsAndThresholds.set(1.5)
        wait_pv_value(
            ctxt_raw,
            alarm_long_pv,
            (1, 6),
            transform=lambda value: (value.alarm.severity, value.alarm.status),
        )
        raw_val = ctxt_raw.get(alarm_long_pv)
        assert raw_val.alarm.severity == 1, \
            'Expected severity=1 (minor) for value=1.5 in (lowAlarm=1.0, lowWarning=2.0), got: {}'.format(
                raw_val.alarm.severity)
        assert raw_val.alarm.status == 6, \
            'Expected status=6 (AlarmLow) for value=1.5, got: {}'.format(raw_val.alarm.status)

        ctxt_raw.close()

    ctxt.close()


if __name__ == '__main__':
    test_local_root()
