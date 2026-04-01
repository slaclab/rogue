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

import numpy as np
import pyrogue as pr
import rogue.interfaces.memory
from conftest import MemoryRoot


class ChildDevice(pr.Device):
    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, **kwargs)
        self.add(pr.RemoteVariable(
            name="ChildRemote",
            offset=0x10,
            bitSize=8,
            base=pr.UInt,
            mode="RW",
        ))


class ParentDevice(pr.Device):
    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, **kwargs)
        self.add(pr.LocalVariable(name="LocalCfg", value=1))
        self.add(pr.RemoteVariable(
            name="RemoteCfg",
            offset=0x0,
            bitSize=8,
            base=pr.UInt,
            mode="RW",
        ))
        self.add(pr.RemoteVariable(
            name="RemoteNoBulk",
            offset=0x4,
            bitSize=8,
            base=pr.UInt,
            mode="RW",
            bulkOpEn=False,
        ))
        self.add(ChildDevice(name="Child", offset=0x20, mem_base=mem_base))


class CommandVarDevice(pr.Device):
    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, **kwargs)

        self.add(pr.LocalVariable(
            name="ThresholdVar",
            value=5,
            lowWarning=4,
            lowAlarm=2,
            highWarning=8,
            highAlarm=10,
            description="Thresholded variable",
        ))

        self.add(pr.LocalVariable(
            name="ArrayVar",
            value=[0, 1, 2, 3],
            description="Indexed variable",
        ))

        self.add(pr.RemoteVariable(
            name="RemoteArray",
            offset=0x48,
            numValues=4,
            valueBits=8,
            valueStride=8,
            base=pr.UInt,
            mode="RW",
            description="Remote indexed variable",
        ))

        self.add(pr.LocalVariable(
            name="MatrixVar",
            value=np.array([[1, 2], [3, 4]]),
            description="Matrix variable",
        ))

        self.add(pr.RemoteCommand(
            name="RemoteCmd",
            offset=0x40,
            bitSize=8,
            base=pr.UInt,
            value=0,
            function=lambda root=None, dev=None, cmd=None, arg=None: ("initial", arg),
            description="Remote command",
        ))


class CoreRoot(MemoryRoot):
    def __init__(self):
        super().__init__(name="root")
        self.add(ParentDevice(name="Parent", mem_base=self._mem))
        self.add(CommandVarDevice(name="CmdDev", mem_base=self._mem, offset=0x100))


def test_device_block_operations_respect_bulk_flags_and_recurse(monkeypatch):
    calls = []

    def fake_start(block, **kwargs):
        calls.append(("start", block.path if hasattr(block, "path") else repr(block), kwargs["type"], kwargs.get("variable")))

    def fake_check(block, **kwargs):
        calls.append(("check", block.path if hasattr(block, "path") else repr(block), None, kwargs.get("variable")))

    monkeypatch.setattr(pr, "startTransaction", fake_start)
    monkeypatch.setattr(pr, "checkTransaction", fake_check)

    with CoreRoot() as root:
        root.Parent.writeBlocks(force=True, recurse=True, checkEach=True)
        root.Parent.verifyBlocks(recurse=True, checkEach=True)
        root.Parent.readBlocks(recurse=True, checkEach=True)
        root.Parent.checkBlocks(recurse=True)

        root.Parent.writeAndVerifyBlocks(force=True, recurse=False, variable=root.Parent.RemoteCfg, checkEach=True)
        root.Parent.readAndCheckBlocks(recurse=False, variable=root.Parent.RemoteCfg, checkEach=True)

    # The bulk-disabled variable should not be included in whole-device block walks.
    started_paths = [path for kind, path, _type, _var in calls if kind == "start"]
    assert all("RemoteNoBulk" not in path for path in started_paths)

    # Variable-specific orchestration should pass the variable through.
    variable_calls = [entry for entry in calls if entry[3] is root.Parent.RemoteCfg]
    assert [entry[2] for entry in variable_calls] == [
        rogue.interfaces.memory.Write,
        rogue.interfaces.memory.Read,
    ]
    assert any(entry[2] == rogue.interfaces.memory.Verify for entry in calls)

    # Child-device recursion should contribute child block activity.
    assert any("Child.ChildRemote" in path for path in started_paths)


def test_remote_command_helpers_replace_function_and_docs(monkeypatch):
    calls = []

    def fake_start(block, **kwargs):
        calls.append((kwargs["type"], kwargs.get("variable"), kwargs.get("index")))

    monkeypatch.setattr(pr, "startTransaction", fake_start)

    with CoreRoot() as root:
        cmd = root.CmdDev.RemoteCmd

        cmd.set(7)
        cmd.get()
        assert calls == [
            (rogue.interfaces.memory.Write, cmd, -1),
            (rogue.interfaces.memory.Read, cmd, -1),
        ]

        cmd.replaceFunction(lambda arg=None: ("replaced", arg))
        assert cmd(9) == ("replaced", 9)
        assert cmd.get(read=False) == 7

        pr.BaseCommand.toggle(cmd)
        pr.BaseCommand.touchZero(cmd)
        pr.BaseCommand.postedTouchOne(cmd)
        assert len(calls) == 6

        # Remote-command docs should include both the command metadata and the
        # address/size details inherited from RemoteVariable.
        buffer = io.StringIO()
        cmd._genDocs(buffer)
        docs = buffer.getvalue()
        assert "RemoteCmd" in docs
        assert "offset" in docs
        assert "varBytes" in docs


def test_variable_alarm_state_update_and_slice_dict_paths():
    with CoreRoot() as root:
        var = root.CmdDev.ThresholdVar

        assert var._alarmState(1) == ("AlarmLoLo", "AlarmMajor")
        assert var._alarmState(3) == ("AlarmLow", "AlarmMinor")
        assert var._alarmState(9) == ("AlarmHigh", "AlarmMinor")
        assert var._alarmState(11) == ("AlarmHiHi", "AlarmMajor")
        assert var._alarmState({"bad": "shape"}) == ("None", "None")

        updates = []
        var.addListener(lambda path, value: updates.append((path, value.value, value.status)))
        var.set(11)
        update = var._doUpdate()
        assert update.value == 11
        assert update.status == "AlarmHiHi"
        assert updates[-1] == (var.path, 11, "AlarmHiHi")

        assert var._getDict(properties=True)["alarmStatus"] == "AlarmHiHi"

        root.CmdDev.RemoteArray._setDict("99", writeEach=False, modes=["RW"], keys=["1"])
        root.CmdDev.RemoteArray._setDict("7,8", writeEach=False, modes=["RW"], keys=["1:3"])
        root.CmdDev.RemoteArray._setDict("5", writeEach=False, modes=["RO"])
        assert list(root.CmdDev.RemoteArray.value()) == [0, 7, 8, 0]

        # Matrix values should still expose type metadata cleanly through VariableValue.
        matrix_value = root.CmdDev.MatrixVar.getVariableValue(read=False)
        assert matrix_value.value.shape == (2, 2)
