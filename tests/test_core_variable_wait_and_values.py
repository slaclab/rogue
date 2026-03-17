#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import threading
import time

import numpy as np
import pyrogue as pr
import rogue.interfaces.memory


class WaitDevice(pr.Device):
    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, **kwargs)
        self.set_calls = []
        self.get_calls = []

        self.add(pr.LocalVariable(
            name="Counter",
            value=0,
            lowWarning=2,
            highAlarm=10,
            groups=["Cfg"],
        ))

        self.add(pr.LocalVariable(
            name="Waveform",
            value=np.array([1, 2, 3]),
            disp="{:d}",
        ))

        self.add(pr.LocalVariable(
            name="GetterOnly",
            mode="RO",
            localGet=self._getter_only,
            typeStr="int",
        ))

        self.add(pr.LocalVariable(
            name="Tracked",
            value=5,
            localSet=self._tracked_set,
            localGet=self._tracked_get,
        ))

        self.add(pr.RemoteVariable(
            name="RemoteArray",
            offset=0x0,
            numValues=4,
            valueBits=8,
            valueStride=8,
            base=pr.UInt,
            mode="RW",
        ))

        self.add(pr.LinkVariable(
            name="ReadOnlyMirror",
            linkedGet=lambda dev=None, var=None, read=True, index=-1, check=True: self.Counter.get(
                read=read,
                index=index,
                check=check,
            ),
        ))

        self.add(pr.LinkVariable(
            name="WriteOnlyMirror",
            linkedSet=lambda dev=None, var=None, value=None, write=True, index=-1, verify=True, check=True: self.Counter.set(
                value,
                index=index,
                write=write,
                verify=verify,
                check=check,
            ),
        ))

        self.add(pr.LinkVariable(
            name="NestedMirror",
            variable=pr.LinkVariable(
                name="InnerMirror",
                variable=self.Counter,
            ),
        ))

    def _getter_only(self, **_kwargs):
        self.get_calls.append("get")
        return 12

    def _tracked_set(self, *, value, changed=None, **_kwargs):
        self.set_calls.append((value, changed))

    def _tracked_get(self, **_kwargs):
        return self.set_calls[-1][0] if self.set_calls else 5


class WaitRoot(pr.Root):
    def __init__(self):
        super().__init__(name="root", pollEn=False)
        self._mem = rogue.interfaces.memory.Emulate(4, 0x4000)
        self.addInterface(self._mem)
        self.add(WaitDevice(name="Dev", mem_base=self._mem))


def test_variable_wait_timeout_rearm_and_get_values(wait_until):
    with WaitRoot() as root:
        waiter = pr.VariableWaitClass(root.Dev.Counter, timeout=0.1)
        assert waiter.wait() is False

        def update_later():
            time.sleep(0.05)
            root.Dev.Counter.set(4)

        thread = threading.Thread(target=update_later)
        thread.start()
        try:
            waiter.arm()
            assert waiter.wait() is True
        finally:
            thread.join(timeout=1.0)

        values = waiter.get_values()
        assert list(values.keys()) == [root.Dev.Counter]
        assert values[root.Dev.Counter].value == 4
        assert values[root.Dev.Counter].updated is True

        # VariableWait() should honor the predicate callback over the current values.
        def set_pair():
            time.sleep(0.05)
            root.Dev.Counter.set(6)
            root.Dev.Tracked.set(9)

        thread = threading.Thread(target=set_pair)
        thread.start()
        try:
            assert pr.VariableWait(
                [root.Dev.Counter, root.Dev.Tracked],
                lambda values: values[0].value >= 6 and values[1].value >= 9,
                timeout=0.5,
            ) is True
        finally:
            thread.join(timeout=1.0)


def test_variable_value_metadata_and_array_display_paths():
    with WaitRoot() as root:
        value = root.Dev.Counter.getVariableValue(read=False)
        assert value.value == 0
        assert value.valueDisp == "0"
        assert value.status == "AlarmLow"
        assert value.severity == "AlarmMinor"
        assert value.updated is False
        assert "VariableValue" in repr(value)

        wave = root.Dev.Waveform.getVariableValue(read=False)
        assert wave.valueDisp == "[1, 2, 3]"
        assert root.Dev.Waveform.parseDisp("[4, 5, 6]").tolist() == [4, 5, 6]

        props = root.Dev.Counter.properties()
        assert props["class"] == "LocalVariable"
        assert props["value"] == 0
        assert props["valueDisp"] == "0"


def test_link_variable_modes_and_dependency_blocks():
    with WaitRoot() as root:
        assert root.Dev.ReadOnlyMirror.mode == "RO"
        assert root.Dev.WriteOnlyMirror.mode == "WO"
        assert root.Dev.NestedMirror.depBlocks == [root.Dev.Counter._block]

        root.Dev.WriteOnlyMirror.set(8)
        assert root.Dev.Counter.value() == 8
        assert root.Dev.ReadOnlyMirror.get() == 8


def test_local_and_remote_variable_edge_operations(monkeypatch):
    posted = []

    def fake_start(block, **kwargs):
        posted.append((block.path, kwargs["type"], kwargs.get("variable"), kwargs.get("index")))

    monkeypatch.setattr(pr, "startTransaction", fake_start)

    with WaitRoot() as root:
        root.Dev.Tracked.set(11)
        assert root.Dev.set_calls[-1] == (11, True)

        root.Dev.Tracked.post(13)
        assert root.Dev.set_calls[-1] == (13, True)

        root.Dev.RemoteArray.setDisp("[7, 8, 9, 10]", write=False)
        assert list(root.Dev.RemoteArray.value()) == [7, 8, 9, 10]

        root.Dev.RemoteArray.post(99, index=2)
        assert posted == [("root.Dev.RemoteArray", rogue.interfaces.memory.Post, root.Dev.RemoteArray, 2)]

        root.Dev.RemoteArray.write(verify=False, check=False)

        # Getter-only local variables should still materialize a native type at finish-init time.
        assert root.Dev.GetterOnly.value() == 12
        assert root.Dev.GetterOnly.nativeType is int
