#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import pyrogue as pr
import pytest
import rogue.interfaces.memory


# ---------------------------------------------------------------------------
# Helper device classes
# ---------------------------------------------------------------------------

class RemoteVarDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add(pr.RemoteVariable(
            name='TestVar',
            offset=0x0,
            bitSize=32,
            base=pr.UInt,
            mode='RW',
        ))


class RemoteCmdDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add(pr.RemoteCommand(
            name='TestCmd',
            offset=0x10,
            bitSize=32,
            base=pr.UInt,
            function=None,
        ))


class LocalOnlyDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add(pr.LocalVariable(name='LocalVar', value=0))
        self.add(pr.LocalCommand(name='LocalCmd', value='', function=lambda arg: None))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_remote_variable_no_membase_raises():
    """TEST-01: Device with RemoteVariable added to Root without memBase raises DeviceError."""
    root = pr.Root(name='root', pollEn=False)
    root.add(RemoteVarDevice(name='BadDev'))
    # Root.start() raises before threads are created; do not call stop() afterward.
    with pytest.raises(pr.DeviceError, match='has RemoteVariables or RemoteCommands but no memBase'):
        root.__enter__()


def test_remote_command_no_membase_raises():
    """TEST-02: Device with RemoteCommand added to Root without memBase raises DeviceError."""
    root = pr.Root(name='root', pollEn=False)
    root.add(RemoteCmdDevice(name='BadCmdDev'))
    # Root.start() raises before threads are created; do not call stop() afterward.
    with pytest.raises(pr.DeviceError, match='has RemoteVariables or RemoteCommands but no memBase'):
        root.__enter__()


def test_local_only_device_no_membase_passes():
    """TEST-03: Device with only LocalVariables/LocalCommands and no memBase starts without error."""
    root = pr.Root(name='root', pollEn=False)
    root.add(LocalOnlyDevice(name='SafeDev'))
    with root:
        assert root.SafeDev.LocalVar.value() == 0


def test_sub_device_inherits_membase():
    """TEST-04: Child device inherits memBase from parent; no error even without explicit memBase."""
    mem = rogue.interfaces.memory.Emulate(4, 0x4000)
    root = pr.Root(name='root', pollEn=False)
    parent = pr.Device(name='Parent', memBase=mem)
    parent.add(RemoteVarDevice(name='Child', offset=0x100))
    root.add(parent)
    with root:
        pass  # No error means child inherited memBase from parent


class CustomRoot(pr.Root):
    """Root subclass to verify _validateMemBase handles Root subclasses."""
    pass


def test_root_subclass_no_membase_raises():
    """TEST-05: Device with RemoteVariable under a Root subclass without memBase raises DeviceError."""
    root = CustomRoot(name='root', pollEn=False)
    root.add(RemoteVarDevice(name='BadDev'))
    with pytest.raises(pr.DeviceError, match='has RemoteVariables or RemoteCommands but no memBase'):
        root.__enter__()


def test_rshift_after_add_passes():
    """TEST-06: Device wired with >> after add() starts and round-trips through Emulate."""
    mem = rogue.interfaces.memory.Emulate(4, 0x4000)
    root = pr.Root(name='root', pollEn=False)
    root.add(RemoteVarDevice(name='Dev'))
    root.Dev >> mem
    with root:
        root.Dev.TestVar.set(0x1234)
        assert root.Dev.TestVar.get() == 0x1234


def test_bus_connect_after_add_passes():
    """TEST-07: Device wired with pr.busConnect after add() starts and round-trips through Emulate."""
    mem = rogue.interfaces.memory.Emulate(4, 0x4000)
    root = pr.Root(name='root', pollEn=False)
    root.add(RemoteVarDevice(name='Dev'))
    pr.busConnect(root.Dev, mem)
    with root:
        root.Dev.TestVar.set(0xABCD)
        assert root.Dev.TestVar.get() == 0xABCD


def test_set_slave_after_add_passes():
    """TEST-08: Device wired with _setSlave after add() starts and round-trips through Emulate."""
    mem = rogue.interfaces.memory.Emulate(4, 0x4000)
    root = pr.Root(name='root', pollEn=False)
    root.add(RemoteCmdDevice(name='Dev'))
    root.Dev._setSlave(mem)
    with root:
        root.Dev.TestCmd()


def test_sub_device_inherits_rewired_slave():
    """TEST-09: Child device under a parent wired with >> after add() inherits the memory path."""
    mem = rogue.interfaces.memory.Emulate(4, 0x4000)
    root = pr.Root(name='root', pollEn=False)
    parent = pr.Device(name='Parent')
    parent.add(RemoteVarDevice(name='Child', offset=0x100))
    root.add(parent)
    root.Parent >> mem
    with root:
        root.Parent.Child.TestVar.set(0x55)
        assert root.Parent.Child.TestVar.get() == 0x55
