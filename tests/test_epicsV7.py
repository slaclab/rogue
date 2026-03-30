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

import platform
import re
import sys
import time
import pyrogue as pr
import pyrogue.protocols.epicsV7
import rogue.interfaces.memory

from p4p.client.thread import Context
import pytest

# TODO: p4p cannot discover the softioc/PVXS server on macOS ARM64 because
# macOS does not support UDP broadcast on the loopback interface (lo0).
# Fix the PVA discovery mechanism and remove this skip.
if sys.platform == 'darwin' and platform.machine() == 'arm64':
    pytest.skip('test_epicsV7 skipped on macOS ARM64: softioc/PVXS PVA '
                'discovery does not work over loopback on this platform',
                allow_module_level=True)

epics_prefix = 'test_ioc_v7'
PropagateTimeout = 10.0
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
                'LocalRoot.SimpleDev.LocalRwUInt32'    : epics_prefix + ':LocalRoot:SimpleDev:LocalRwUInt32',
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


def test_pv_name_hash():
    """Unit tests for _make_epicsV7_suffix and _EPICS_MAX_NAME_LEN -- no IOC required."""
    from pyrogue.protocols.epicsV7 import _make_epicsV7_suffix, _EPICS_MAX_NAME_LEN

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
        # Note: softioc uses signed int64Out for UInt64; test with a value in int64 range
        pv_name = device_epics_prefix + ':LocalRwUInt64'
        test_value = 9223372036854775806  # INT64_MAX - 1, fits in int64Out without overflow
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
        # Note: softioc uses signed longOut for UInt32; test with a value in int32 range
        pv_name = device_epics_prefix + ':LocalRwUInt32'
        test_value = 2147483647  # INT32_MAX, fits in longOut without overflow
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
        wait_pv_value(ctxt, pv_name, round(test_value, 4), transform=lambda value: round(value, 4))
        test_result = round(ctxt.get(pv_name), 4)
        if test_result != round(test_value, 4):
            raise AssertionError('Float32: pv_name={}: test_value={}; test_result={}'.format(
                pv_name, test_value, test_result))

        # TEST-19: Float64 type
        pv_name = device_epics_prefix + ':LocalRwFloat64'
        test_value = 2.718281828459045
        ctxt.put(pv_name, test_value)
        wait_pv_value(ctxt, pv_name, round(test_value, 10), transform=lambda value: round(value, 10))
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

        # TEST-22: list nativeType (longStringIn/Out) — verify PV is accessible
        pv_name = device_epics_prefix + ':LocalRwList'
        wait_pv_value(ctxt, pv_name, True, transform=lambda v: isinstance(v, str) and len(v) > 0)

        # TEST-23: dict nativeType (longStringIn/Out) — verify PV is accessible
        pv_name = device_epics_prefix + ':LocalRwDict'
        wait_pv_value(ctxt, pv_name, True, transform=lambda v: isinstance(v, str) and len(v) > 0)

        # TEST-24: RO LocalVariable (longIn) — verifies _varUpdated works for In records.
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

        # ---- Long PV name hashing tests (Phase 2: HASH-05, OPS-01, OPS-02, TEST-03) ----

        # Verify the long-named PVs are accessible via PVA using hashed CA names.
        # The suffix is hashed to tail_XXXXXXXXXX when base:suffix > 60 chars.
        from pyrogue.protocols.epicsV7 import _make_epicsV7_suffix

        long_var_name_1 = 'ThisIsAVeryLongVariableNameThatExceedsSixtyCharacterLimit'
        long_suffix_1 = 'LocalRoot:LongNameSubDev:' + long_var_name_1
        hashed_suffix_1 = _make_epicsV7_suffix(epics_prefix, long_suffix_1)
        hashed_pv_1 = epics_prefix + ':' + hashed_suffix_1

        long_var_name_2 = 'AnotherExtremelyLongVariableNameForTestingHashBehavior'
        long_suffix_2 = 'LocalRoot:LongNameSubDev:' + long_var_name_2
        hashed_suffix_2 = _make_epicsV7_suffix(epics_prefix, long_suffix_2)
        hashed_pv_2 = epics_prefix + ':' + hashed_suffix_2

        short_pv = epics_prefix + ':LocalRoot:LongNameSubDev:ShortVar'

        # TEST-03a: Verify hashed PVs are reachable (HASH-05)
        # The hashed suffix should start with 'tail_' since the full name exceeds 60 chars
        assert hashed_suffix_1.startswith('tail_'), \
            'Expected hashed suffix for long var 1, got: {}'.format(hashed_suffix_1)
        assert hashed_suffix_2.startswith('tail_'), \
            'Expected hashed suffix for long var 2, got: {}'.format(hashed_suffix_2)

        # Verify PVs are accessible via the hashed CA names
        wait_pv_value(ctxt, hashed_pv_1, 0)
        wait_pv_value(ctxt, hashed_pv_2, True,
                      transform=lambda v: abs(v - 3.14) < 0.01)

        # TEST-03b: RW round-trip on a hashed PV (HASH-05)
        test_value = 777
        ctxt.put(hashed_pv_1, test_value)
        wait_pv_value(ctxt, hashed_pv_1, test_value)
        test_result = ctxt.get(hashed_pv_1)
        if test_result != test_value:
            raise AssertionError(
                'Long-name PV RW failed: pv_name={}: expected={}; got={}'.format(
                    hashed_pv_1, test_value, test_result))

        # TEST-03c: Short-named PV in same device is NOT hashed (zero regression)
        wait_pv_value(ctxt, short_pv, 42)
        test_value = 99
        ctxt.put(short_pv, test_value)
        wait_pv_value(ctxt, short_pv, test_value)
        test_result = ctxt.get(short_pv)
        if test_result != test_value:
            raise AssertionError(
                'Short-name PV in LongNameSubDev failed: expected={}; got={}'.format(
                    test_value, test_result))

        # TEST-03d: list() returns full long names, not hashed names (OPS-01)
        pv_map = root.epics.list()
        long_path_1 = 'LocalRoot.LongNameSubDev.' + long_var_name_1
        full_long_name_1 = epics_prefix + ':' + long_suffix_1
        assert long_path_1 in pv_map, \
            'list() missing long-named PV path: {}'.format(long_path_1)
        assert pv_map[long_path_1] == full_long_name_1, \
            'list() should show full long name, got: {}'.format(pv_map[long_path_1])

        # TEST-03e: dump() shows annotation for hashed PVs (OPS-02)
        import io
        import sys
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

        # TEST-03f: Verify all existing short-named PVs still work (zero regression)
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

        # ---- PVA long-name alias tests (Phase 3: PVA-01 through PVA-05, TEST-02) ----

        # Compute full long PVA names for the hashed PVs
        long_pv_full_1 = epics_prefix + ':' + long_suffix_1
        long_pv_full_2 = epics_prefix + ':' + long_suffix_2

        # TEST-02a: pvget on full long name returns current value (PVA-01, PVA-05)
        # The hashed PV was left at test_value=777 from TEST-03b above
        wait_pv_value(ctxt, long_pv_full_1, 777)

        # TEST-02b: pvput via full long name, read back via long name (PVA-02)
        test_value = 888
        ctxt.put(long_pv_full_1, test_value)
        wait_pv_value(ctxt, long_pv_full_1, test_value)
        test_result = ctxt.get(long_pv_full_1)
        if test_result != test_value:
            raise AssertionError(
                'PVA long-name put/get failed: pv={}: expected={}; got={}'.format(
                    long_pv_full_1, test_value, test_result))

        # TEST-02c: PVA write via long name visible on hashed CA name (PVA-03 fan-out)
        test_value = 555
        ctxt.put(long_pv_full_1, test_value)
        wait_pv_value(ctxt, hashed_pv_1, test_value)
        test_result = ctxt.get(hashed_pv_1)
        if test_result != test_value:
            raise AssertionError(
                'PVA->CA fan-out failed: long={} CA={}: expected={}; got={}'.format(
                    long_pv_full_1, hashed_pv_1, test_value, test_result))

        # TEST-02d: CA write via short name visible on full long name (PVA-03 reverse fan-out)
        test_value = 444
        ctxt.put(hashed_pv_1, test_value)
        wait_pv_value(ctxt, long_pv_full_1, test_value)
        test_result = ctxt.get(long_pv_full_1)
        if test_result != test_value:
            raise AssertionError(
                'CA->PVA fan-out failed: CA={} long={}: expected={}; got={}'.format(
                    hashed_pv_1, long_pv_full_1, test_value, test_result))

        # TEST-02e: Second hashed PV (float) accessible via full long name (PVA-01)
        wait_pv_value(ctxt, long_pv_full_2, True,
                      transform=lambda v: isinstance(v, float))
        test_value = 2.718
        ctxt.put(long_pv_full_2, test_value)
        wait_pv_value(ctxt, long_pv_full_2, round(test_value, 3),
                      transform=lambda v: round(v, 3))

        # TEST-02f: Short-named PVs unaffected by PVA alias layer (zero regression)
        std_pv = epics_prefix + ':LocalRoot:SimpleDev:LocalRwInt'
        test_value = 54321
        ctxt.put(std_pv, test_value)
        wait_pv_value(ctxt, std_pv, test_value)
        test_result = ctxt.get(std_pv)
        if test_result != test_value:
            raise AssertionError(
                'Zero-regression after PVA alias layer: expected={}; got={}'.format(
                    test_value, test_result))

    ctxt.close()


if __name__ == '__main__':
    test_local_root()
