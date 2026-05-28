#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import pytest
import pyrogue as pr
from conftest import MemoryRoot


# ---------------------------------------------------------------------------
# Helpers — plain functions (not lambdas) so the arg introspection in
# BaseCommand.__init__ succeeds without raising on C-extension paths.
# ---------------------------------------------------------------------------

def _noop_fn(root=None, dev=None, cmd=None, arg=None):
    """No-op command function for construction tests."""
    return None


# ---------------------------------------------------------------------------
# Device / Root definitions — RemoteCommand cases (need memory backing)
# ---------------------------------------------------------------------------

class _AsyncRegDevice(pr.Device):
    """Device that adds a RemoteCommand with nonBlocking=True."""

    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, **kwargs)
        # The explicit `nonBlocking` kwarg on RemoteCommand.__init__ routes
        # nonBlocking only to BaseCommand.__init__ and keeps it out of the
        # **kwargs handed to pr.RemoteVariable.__init__.  pr.RemoteVariable
        # accepts **kwargs and silently absorbs unknown keywords, so this
        # routing is documentation rather than a crash fix.
        self.add(pr.RemoteCommand(
            name='AsyncReg',
            offset=0x00,
            bitSize=8,
            base=pr.UInt,
            value=0,
            function=_noop_fn,
            nonBlocking=True,
            description='Non-blocking remote command — construction guard.',
        ))


class _AsyncRegRoot(MemoryRoot):
    def __init__(self):
        super().__init__(name='AsyncRegRoot')
        self.add(_AsyncRegDevice(name='Dev', mem_base=self._mem))


# ---------------------------------------------------------------------------
# Device / Root definitions — default RemoteCommand (backward-compat)
# ---------------------------------------------------------------------------

class _SyncRegDevice(pr.Device):
    """Device that adds a default (no nonBlocking kwarg) RemoteCommand."""

    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, **kwargs)
        self.add(pr.RemoteCommand(
            name='SyncReg',
            offset=0x00,
            bitSize=8,
            base=pr.UInt,
            value=0,
            function=_noop_fn,
            description='Default (sync) remote command — backward-compat guard.',
        ))


class _SyncRegRoot(MemoryRoot):
    def __init__(self):
        super().__init__(name='SyncRegRoot')
        self.add(_SyncRegDevice(name='Dev', mem_base=self._mem))


# ---------------------------------------------------------------------------
# Device / Root definitions — sibling-name collision (LocalCommand path)
# ---------------------------------------------------------------------------

class _CollisionDevice(pr.Device):
    """Device with a pre-existing 'FooRunning' child before a nonBlocking
    LocalCommand named 'Foo' is added.  _rootAttached must detect the
    collision and raise pr.NodeError."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Pre-plant the colliding variable BEFORE the command.
        self.add(pr.LocalVariable(
            name='FooRunning',
            value=False,
            description='Pre-existing variable whose name collides with the generated sibling.',
        ))
        # Without the pre-injection collision check in _rootAttached,
        # parent._nodes['FooRunning'] would be silently overwritten by the
        # auto-generated sibling, destroying the pre-existing variable.
        self.add(pr.LocalCommand(
            name='Foo',
            function=_noop_fn,
            nonBlocking=True,
            description='nonBlocking LocalCommand whose FooRunning sibling name collides.',
        ))


class _CollisionRoot(pr.Root):
    def __init__(self):
        super().__init__(name='CollisionRoot', pollEn=False)
        self.add(_CollisionDevice(name='Dev'))


# ---------------------------------------------------------------------------
# Device / Root definitions — non-collision control (LocalCommand path)
# ---------------------------------------------------------------------------

class _BarDevice(pr.Device):
    """Device with a nonBlocking LocalCommand named 'Bar' and NO pre-existing
    BarRunning/BarResult/BarError children.  Must attach cleanly."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add(pr.LocalCommand(
            name='Bar',
            function=_noop_fn,
            nonBlocking=True,
            description='Non-blocking LocalCommand with no colliding siblings.',
        ))


class _BarRoot(pr.Root):
    def __init__(self):
        super().__init__(name='BarRoot', pollEn=False)
        self.add(_BarDevice(name='Dev'))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_remote_command_nonblocking_constructs():
    """RemoteCommand(nonBlocking=True) constructs, attaches, and auto-injects
    its three sibling status variables (AsyncRegRunning, AsyncRegResult,
    AsyncRegError) on start().
    """
    with _AsyncRegRoot() as root:
        # Construction and start() completed without TypeError.
        dev = root.Dev
        # The three sibling status variables must exist on the parent Device.
        assert 'AsyncRegRunning' in dev.nodes, \
            "AsyncRegRunning sibling not injected by _rootAttached"
        assert 'AsyncRegResult' in dev.nodes, \
            "AsyncRegResult sibling not injected by _rootAttached"
        assert 'AsyncRegError' in dev.nodes, \
            "AsyncRegError sibling not injected by _rootAttached"


def test_remote_command_default_unchanged():
    """Backward-compat: a RemoteCommand constructed WITHOUT nonBlocking must
    attach cleanly and must NOT create any sibling status variables.  Pins the
    promise that default BaseCommand behaviour is unchanged.
    """
    with _SyncRegRoot() as root:
        dev = root.Dev
        assert 'SyncReg' in dev.nodes, "SyncReg command not found on device"
        assert 'SyncRegRunning' not in dev.nodes, \
            "SyncRegRunning sibling must not exist for a default (sync) RemoteCommand"
        assert 'SyncRegResult' not in dev.nodes, \
            "SyncRegResult sibling must not exist for a default (sync) RemoteCommand"
        assert 'SyncRegError' not in dev.nodes, \
            "SyncRegError sibling must not exist for a default (sync) RemoteCommand"


def test_sibling_injection_collision_raises_nodeerror():
    """When a parent Device already contains a child whose name collides with
    a generated {name}Running / {name}Result / {name}Error sibling,
    BaseCommand._rootAttached must raise pr.NodeError BEFORE any
    parent._nodes mutation — the pre-existing node must not be overwritten.
    """
    with pytest.raises(pr.NodeError):
        with _CollisionRoot():
            pass


def test_sibling_injection_no_collision_ok():
    """A nonBlocking LocalCommand with no pre-existing sibling name collisions
    must attach cleanly and create its three status siblings.  Proves the
    collision guard does not false-positive on the normal path.
    """
    with _BarRoot() as root:
        dev = root.Dev
        assert 'Bar' in dev.nodes, "Bar command not found on device"
        assert 'BarRunning' in dev.nodes, \
            "BarRunning sibling not injected for non-colliding nonBlocking LocalCommand"
        assert 'BarResult' in dev.nodes, \
            "BarResult sibling not injected for non-colliding nonBlocking LocalCommand"
        assert 'BarError' in dev.nodes, \
            "BarError sibling not injected for non-colliding nonBlocking LocalCommand"
