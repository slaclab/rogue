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
import sys
import time
import pyrogue as pr
import pyrogue.protocols.epicsV4
import rogue.interfaces.memory
import pytest

from p4p.client.thread import Context
from p4p.nt import NTURI

# TODO: p4p cannot discover the EpicsPvServer on macOS ARM64 because
# macOS does not support UDP broadcast on the loopback interface (lo0).
# Fix the PVA discovery mechanism and remove this skip.
if sys.platform == 'darwin' and platform.machine() == 'arm64':
    pytest.skip('test_epicsV4 skipped on macOS ARM64: PVA discovery does '
                'not work over loopback on this platform',
                allow_module_level=True)

pytestmark = [pytest.mark.integration, pytest.mark.epics]

epics_prefix='test_ioc'
PV_DISCOVERY_TIMEOUT = 10.0
PropagateTimeout = 5.0
POLL_INTERVAL = 0.05

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
        mc = rogue.interfaces.memory.TcpClient("127.0.0.1",9070, True)
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
            # PV map
            pv_map = {
                'LocalRoot.SimpleDev.LocalRwInt'      : epics_prefix+':LocalRoot:SimpleDev:LocalRwInt',
                'LocalRoot.SimpleDev.LocalWoInt'      : epics_prefix+':LocalRoot:SimpleDev:LocalWoInt',
                'LocalRoot.SimpleDev.LocalRwFloat'    : epics_prefix+':LocalRoot:SimpleDev:LocalRwFloat',
                'LocalRoot.SimpleDev.RemoteRwInt'     : epics_prefix+':LocalRoot:SimpleDev:RemoteRwInt',
                'LocalRoot.SimpleDev.RemoteWoInt'     : epics_prefix+':LocalRoot:SimpleDev:RemoteWoInt',
                'LocalRoot.SimpleDev.ResetLocalRwInt' : epics_prefix+':LocalRoot:SimpleDev:ResetLocalRwInt',
                'LocalRoot.SimpleDev.SetLocalRwInt'   : epics_prefix+':LocalRoot:SimpleDev:SetLocalRwInt',
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


def make_pva_client(root):
    """Build a p4p client wired directly to the running EpicsPvServer.

    The server and client must rendezvous without UDP broadcast/search: that
    discovery path is unreliable over loopback on CI runners (the same
    limitation that disables this test on macOS ARM64), and the EPICS default
    ports are not always bindable on CI, so the server may fall back to an
    ephemeral port.

    Read the server's actual bound TCP port and point the client at it via
    EPICS_PVA_NAME_SERVERS. In PVXS this performs the channel search over a
    direct TCP connection to the named server, bypassing UDP broadcast and UDP
    search (the client resolves the PV even with every UDP search destination
    removed). useenv=False keeps ambient EPICS_* settings from re-introducing
    UDP discovery.

    Raises RuntimeError if the EPICS server has not started or its config does
    not expose a server port, so an infrastructure or p4p API change surfaces as
    a clear message rather than an opaque AttributeError/KeyError.
    """
    server = getattr(root.epics, '_server', None)
    if server is None:
        raise RuntimeError('EpicsPvServer is not started; cannot determine the '
                           'PVA server port for the test client')

    conf = server.conf()
    port = conf.get('EPICS_PVA_SERVER_PORT')
    if not port:
        raise RuntimeError('EpicsPvServer config has no EPICS_PVA_SERVER_PORT; '
                           'cannot determine the PVA server port for the test '
                           'client (config keys: {})'.format(sorted(conf)))
    return Context('pva', conf={
        'EPICS_PVA_NAME_SERVERS': '127.0.0.1:{}'.format(port),
        'EPICS_PVA_AUTO_ADDR_LIST': 'NO',
        'EPICS_PVA_ADDR_LIST': '',
    }, useenv=False)


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

def test_local_root():
    """
    Test Epics Server
    """
    # Test both autogeneration and mapping of PV names
    pv_map_states = [False, True]

    # setup the P4P client
    # https://mdavidsaver.github.io/p4p/client.html#usage
    print( Context.providers() )

    for s in pv_map_states:
        with LocalRootWithEpics(use_map=s) as root:
            # Device EPICS PV name prefix
            device_epics_prefix=epics_prefix+':LocalRoot:SimpleDev'

            # Test dump method
            root.epics.dump()

            # Test list method
            root.epics.list()

            # Build a client bound directly to this server instance. Each
            # iteration starts a fresh server, so build a fresh client.
            try:
                client = make_pva_client(root)
            except RuntimeError as exc:
                pytest.skip(f'EPICS PVA socket setup unavailable: {exc}')

            # The context manager guarantees the client is closed before the
            # server is torn down, even if an assertion below fails.
            with client as ctxt:
                # Wait for PVs to become visible through the EPICS server.
                wait_pv_value(ctxt, device_epics_prefix+':LocalRwInt', 0, timeout=PV_DISCOVERY_TIMEOUT)

                # Test RW a variable holding an scalar value
                pv_name=device_epics_prefix+':LocalRwInt'
                test_value=314
                ctxt.put(pv_name, test_value)
                wait_pv_value(ctxt, pv_name, test_value)
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
                wait_pv_value(ctxt, pv_name, test_value, transform=lambda value: round(value,2))
                test_result=round(ctxt.get(pv_name),2)
                if test_result != test_value:
                    raise AssertionError('pvStates={} pv_name={}: test_value={}; test_result={}'.format(s, pv_name, test_value, test_result))

                # Test RW a variable holding an scalar value
                pv_name=device_epics_prefix+':RemoteRwInt'
                test_value=314
                ctxt.put(pv_name, test_value)
                wait_pv_value(ctxt, pv_name, test_value)
                test_result=ctxt.get(pv_name)
                if test_result != test_value:
                    raise AssertionError('pv_name={}: test_value={}; test_result={}'.format(pv_name, test_value, test_result))

                # Test WO a variable holding an scalar value
                pv_name=device_epics_prefix+':RemoteWoInt'
                test_value=314
                ctxt.put(pv_name, test_value)

                # Test RPC: set LocalRwInt to non-zero, call rpc to reset, verify it's zero
                pv_name=device_epics_prefix+':LocalRwInt'
                rpc_pv=device_epics_prefix+':ResetLocalRwInt'
                test_value=42
                ctxt.put(pv_name, test_value)
                wait_pv_value(ctxt, pv_name, test_value)

                # Use a separate context for rpc() to avoid tainting the main
                # context's NTScalar unwrapping for subsequent get() calls. The
                # context manager guarantees the client is closed even if rpc()
                # raises.
                uri = NTURI([])
                with make_pva_client(root) as rpc_ctxt:
                    rpc_ctxt.rpc(rpc_pv, uri.wrap(rpc_pv))

                wait_pv_value(ctxt, pv_name, 0)
                test_result=ctxt.get(pv_name)
                if test_result != 0:
                    raise AssertionError('RPC reset failed: pv_name={}: expected=0; test_result={}'.format(pv_name, test_result))

                # Test RPC with argument: call rpc with arg to set LocalRwInt to a specific value
                pv_name=device_epics_prefix+':LocalRwInt'
                rpc_pv=device_epics_prefix+':SetLocalRwInt'
                test_value=99
                uri = NTURI([('arg', 'i')])
                with make_pva_client(root) as rpc_ctxt:
                    rpc_ctxt.rpc(rpc_pv, uri.wrap(rpc_pv, kws={'arg': test_value}))

                wait_pv_value(ctxt, pv_name, test_value)
                test_result=ctxt.get(pv_name)
                if test_result != test_value:
                    raise AssertionError('RPC set failed: pv_name={}: expected={}; test_result={}'.format(pv_name, test_value, test_result))

if __name__ == "__main__":
    test_local_root()
