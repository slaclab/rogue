#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""Tests for pre-write listener infrastructure (ESROGUE-743)."""

import pytest
import pyrogue as pr
import rogue.interfaces.memory


class PreWriteDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add(pr.LocalVariable(name='Target', value=0, mode='RW'))
        self.add(pr.LocalVariable(name='StateSource', value=42, mode='RW'))
        self.add(pr.LocalVariable(name='Guard', value=False, mode='RW'))


class PreWriteRoot(pr.Root):
    def __init__(self):
        super().__init__(name='root', pollEn=False)
        self.add(PreWriteDevice(name='Dev'))


class RemotePreWriteDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add(pr.RemoteVariable(
            name='Reg', offset=0x0, bitSize=32, base=pr.UInt, mode='RW',
        ))
        self.add(pr.RemoteVariable(
            name='Status', offset=0x4, bitSize=32, base=pr.UInt, mode='RW',
        ))


class RemotePreWriteRoot(pr.Root):
    def __init__(self):
        super().__init__(name='root', pollEn=False)
        mem = rogue.interfaces.memory.Emulate(4, 0x1000)
        self.addInterface(mem)
        self.add(RemotePreWriteDevice(name='Dev', memBase=mem))


def test_listener_allows_write():
    """Pre-write listener that returns None allows write normally."""
    called = []

    def allow(path, value, state):
        called.append((path, value, state))
        return None

    with PreWriteRoot() as root:
        root.Dev.Target.addPreWriteListener(allow)
        root.Dev.Target.set(10)
        assert root.Dev.Target.value() == 10
        assert len(called) == 1
        assert called[0][1] == 10


def test_listener_blocks_write():
    """WriteBlockedError from listener prevents the write."""
    with PreWriteRoot() as root:
        root.Dev.Target.set(5)

        def block(path, value, state):
            raise pr.WriteBlockedError(path, "camera acquiring")

        root.Dev.Target.addPreWriteListener(block)

        with pytest.raises(pr.WriteBlockedError, match="camera acquiring"):
            root.Dev.Target.set(99)

        assert root.Dev.Target.value() == 5


def test_listener_modifies_value():
    """Listener can return a modified value to be written instead."""
    def clamp(path, value, state):
        if value > 100:
            return 100
        return None

    with PreWriteRoot() as root:
        root.Dev.Target.addPreWriteListener(clamp)
        root.Dev.Target.set(200)
        assert root.Dev.Target.value() == 100

        root.Dev.Target.set(50)
        assert root.Dev.Target.value() == 50


def test_multiple_listeners_chain_value():
    """Multiple listeners modify value in registration order."""
    def double(path, value, state):
        return value * 2

    def add_one(path, value, state):
        return value + 1

    with PreWriteRoot() as root:
        root.Dev.Target.addPreWriteListener(double)
        root.Dev.Target.addPreWriteListener(add_one)
        root.Dev.Target.set(5)
        # 5 * 2 = 10, then 10 + 1 = 11
        assert root.Dev.Target.value() == 11


def test_state_snapshot():
    """State dict contains current values of configured stateVars."""
    captured_state = []

    def check_state(path, value, state):
        captured_state.append(state.copy())
        return None

    with PreWriteRoot() as root:
        root.Dev.StateSource.set(99)
        root.Dev.Target.addPreWriteListener(
            check_state,
            stateVars=[root.Dev.StateSource],
        )
        root.Dev.Target.set(7)

        assert len(captured_state) == 1
        assert root.Dev.StateSource.path in captured_state[0]
        assert captured_state[0][root.Dev.StateSource.path] == 99


def test_device_level_blocks_child():
    """Device-level pre-write listener can block any child variable write."""
    with PreWriteRoot() as root:
        root.Dev.Target.set(5)

        def device_guard(path, value, state):
            raise pr.WriteBlockedError(path, "device locked")

        root.Dev.addPreWriteListener(device_guard)

        with pytest.raises(pr.WriteBlockedError, match="device locked"):
            root.Dev.Target.set(99)

        assert root.Dev.Target.value() == 5


def test_device_level_fires_before_variable_level():
    """Device-level listeners fire before variable-level listeners."""
    order = []

    def dev_listener(path, value, state):
        order.append('device')
        return None

    def var_listener(path, value, state):
        order.append('variable')
        return None

    with PreWriteRoot() as root:
        root.Dev.addPreWriteListener(dev_listener)
        root.Dev.Target.addPreWriteListener(var_listener)
        root.Dev.Target.set(1)

        assert order == ['device', 'variable']


def test_first_rejection_stops_evaluation():
    """Once a listener raises, subsequent listeners are not called."""
    second_called = []

    def blocker(path, value, state):
        raise pr.WriteBlockedError(path, "blocked")

    def second(path, value, state):
        second_called.append(True)
        return None

    with PreWriteRoot() as root:
        root.Dev.Target.addPreWriteListener(blocker)
        root.Dev.Target.addPreWriteListener(second)

        with pytest.raises(pr.WriteBlockedError):
            root.Dev.Target.set(1)

        assert second_called == []


def test_del_pre_write_listener():
    """Removing a listener stops it from firing."""
    called = []

    def listener(path, value, state):
        called.append(True)
        return None

    with PreWriteRoot() as root:
        root.Dev.Target.addPreWriteListener(listener)
        root.Dev.Target.set(1)
        assert len(called) == 1

        root.Dev.Target.delPreWriteListener(listener)
        root.Dev.Target.set(2)
        assert len(called) == 1


def test_set_write_false_does_not_fire():
    """set(write=False) does not trigger pre-write listeners."""
    called = []

    def listener(path, value, state):
        called.append(True)
        return None

    with PreWriteRoot() as root:
        root.Dev.Target.addPreWriteListener(listener)
        root.Dev.Target.set(10, write=False)
        assert called == []


def test_post_fires_listener():
    """post() triggers pre-write listeners."""
    called = []

    def listener(path, value, state):
        called.append(value)
        return None

    with PreWriteRoot() as root:
        root.Dev.Target.addPreWriteListener(listener)
        root.Dev.Target.post(7)
        assert called == [7]
        assert root.Dev.Target.value() == 7


def test_non_write_blocked_exception_propagates():
    """Non-WriteBlockedError exceptions propagate without leaving dirty state."""
    with PreWriteRoot() as root:
        root.Dev.Target.set(5)

        def bad_listener(path, value, state):
            raise RuntimeError("unexpected error")

        root.Dev.Target.addPreWriteListener(bad_listener)

        with pytest.raises(RuntimeError, match="unexpected error"):
            root.Dev.Target.set(99)

        assert root.Dev.Target.value() == 5


def test_remote_variable_set_blocked():
    """Pre-write listener blocks RemoteVariable.set() correctly."""
    with RemotePreWriteRoot() as root:
        root.Dev.Reg.set(100)

        def guard(path, value, state):
            if state.get(root.Dev.Status.path, 0) != 0:
                raise pr.WriteBlockedError(path, "status not idle")
            return None

        root.Dev.Reg.addPreWriteListener(guard, stateVars=[root.Dev.Status])

        # Status is 0, write should succeed
        root.Dev.Reg.set(200)
        assert root.Dev.Reg.get(read=False) == 200

        # Set status to non-zero, write should be blocked
        root.Dev.Status.set(1)
        with pytest.raises(pr.WriteBlockedError, match="status not idle"):
            root.Dev.Reg.set(300)

        assert root.Dev.Reg.get(read=False) == 200


def test_remote_variable_post_blocked():
    """Pre-write listener blocks RemoteVariable.post() correctly."""
    with RemotePreWriteRoot() as root:
        root.Dev.Reg.set(50)

        def block(path, value, state):
            raise pr.WriteBlockedError(path, "blocked")

        root.Dev.Reg.addPreWriteListener(block)

        with pytest.raises(pr.WriteBlockedError):
            root.Dev.Reg.post(999)

        assert root.Dev.Reg.get(read=False) == 50


def test_remote_variable_value_modification():
    """Pre-write listener can modify RemoteVariable write value."""
    def cap_at_255(path, value, state):
        if value > 255:
            return 255
        return None

    with RemotePreWriteRoot() as root:
        root.Dev.Reg.addPreWriteListener(cap_at_255)
        root.Dev.Reg.set(1000)
        assert root.Dev.Reg.get(read=False) == 255

        root.Dev.Reg.set(100)
        assert root.Dev.Reg.get(read=False) == 100


def test_no_listeners_no_overhead():
    """With no listeners registered, _runPreWriteListeners is a fast no-op."""
    with PreWriteRoot() as root:
        # Just verify it works without listeners (fast path)
        root.Dev.Target.set(42)
        assert root.Dev.Target.value() == 42


def test_device_level_value_modification():
    """Device-level listener can modify values for child variables."""
    def always_zero(path, value, state):
        return 0

    with PreWriteRoot() as root:
        root.Dev.addPreWriteListener(always_zero)
        root.Dev.Target.set(999)
        assert root.Dev.Target.value() == 0
