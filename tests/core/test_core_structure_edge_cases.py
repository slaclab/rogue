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
from conftest import MemoryRoot


class ResetChild(pr.Device):
    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, **kwargs)
        self.initialize_calls = 0
        self.hard_reset_calls = 0
        self.count_reset_calls = 0
        self.enable_events = []

        self.add(pr.RemoteVariable(
            name="ChildRemote",
            offset=0x10,
            bitSize=8,
            base=pr.UInt,
            mode="RW",
        ))

    def initialize(self):
        self.initialize_calls += 1

    def hardReset(self):
        self.hard_reset_calls += 1

    def countReset(self):
        self.count_reset_calls += 1

    def enableChanged(self, value):
        self.enable_events.append(value)


class ResetParent(pr.Device):
    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, **kwargs)
        self.enable_events = []

        self.add(pr.LocalVariable(name="ConfigValue", value=1, groups=["Cfg"]))
        self.add(pr.LocalVariable(name="StatusValue", value=2, mode="RO", groups=["Status"]))
        self.add(pr.LocalVariable(name="PolledValue", value=3, groups=["Cfg"], pollInterval=2.0))
        self.add(pr.RemoteVariable(
            name="RemoteCfg",
            offset=0x0,
            bitSize=8,
            base=pr.UInt,
            mode="RW",
        ))
        self.add(ResetChild(name="Child", offset=0x20, mem_base=mem_base))

    def enableChanged(self, value):
        self.enable_events.append(value)


class StructureRoot(MemoryRoot):
    def __init__(self):
        super().__init__(name="root")
        self.initialize_calls = 0
        self.add(ResetParent(name="Parent", mem_base=self._mem))
        self.add(pr.LocalVariable(
            name="HexValue",
            value=15,
            disp="0x{:x}",
        ))
        self.add(pr.LocalCommand(
            name="DoThing",
            value=0,
            function=self._record_command,
        ))
        self.add(pr.LocalCommand(
            name="FmtCmd",
            retValue=255,
            retDisp="0x{:x}",
            function=lambda: 255,
        ))
        self.command_args = []

    def initialize(self):
        self.initialize_calls += 1
        super().initialize()

    def _record_command(self, arg):
        self.command_args.append(arg)
        return arg


class FakeCommandTarget:
    def __init__(self, *, read_back=None):
        self.set_calls = []
        self.post_calls = []
        self.read_back = read_back
        self.path = "Fake.Cmd"

    def set(self, value):
        self.set_calls.append(value)

    def post(self, value):
        self.post_calls.append(value)

    def get(self):
        return self.read_back


def test_root_listener_done_callback_and_cpp_variable_listener(wait_until):
    root_updates = []
    done_calls = []
    disp_updates = []

    with StructureRoot() as root:
        root.addVarListener(
            lambda path, value: root_updates.append((path, value.value)),
            done=lambda: done_calls.append("done"),
            incGroups="Cfg",
        )
        root.waitOnUpdate()
        root_updates.clear()
        done_calls.clear()

        # _addListenerCpp wraps each registration in a fresh lambda, so two
        # registrations should generate two display-string callbacks.
        def cpp_listener(path, value):
            disp_updates.append((path, value))

        root.HexValue._addListenerCpp(cpp_listener)
        root.HexValue._addListenerCpp(cpp_listener)

        with root.updateGroup():
            root.Parent.ConfigValue.set(9)
            root.Parent.StatusValue.set(10)
            root.HexValue.set(31)

        assert wait_until(lambda: root_updates == [("root.Parent.ConfigValue", 9)])
        assert done_calls == ["done"]
        assert disp_updates == [("root.HexValue", "0x1f"), ("root.HexValue", "0x1f")]


def test_device_force_check_each_recurse_false_and_reset_propagation(monkeypatch):
    starts = []

    def fake_start(block, **kwargs):
        starts.append((block.path, kwargs["type"], kwargs.get("checkEach")))

    monkeypatch.setattr(pr, "startTransaction", fake_start)

    with StructureRoot() as root:
        root.Parent.forceCheckEach = True
        root.Parent.writeBlocks(recurse=False, checkEach=False)
        root.Parent.readBlocks(recurse=False, checkEach=False)
        root.Parent.verifyBlocks(recurse=False, checkEach=False)

        # recurse=False should stay on the parent device, but still inherit
        # forceCheckEach when the caller leaves checkEach False. Whole-device
        # walks still include local blocks, so the critical boundary here is
        # that child-device blocks are absent.
        assert all(check_each is True for _, _, check_each in starts)
        assert any(path == "root.Parent.RemoteCfg" for path, _, _ in starts)
        assert all("root.Parent.Child" not in path for path, _, _ in starts)

        root.initialize()
        root.hardReset()
        root.countReset()

        assert root.Parent.Child.initialize_calls == 1
        assert root.Parent.Child.hard_reset_calls == 1
        assert root.Parent.Child.count_reset_calls == 1


def test_device_enable_changes_propagate_to_blocks_and_children(wait_until):
    with StructureRoot() as root:
        block_calls = []

        # Capture the effective enable state pushed into each built block.
        for block in root.Parent._blocks + root.Parent.Child._blocks:
            original = block.setEnable

            def recorder(value, *, _block=block, _original=original):
                block_calls.append((_block.path, value))
                _original(value)

            block.setEnable = recorder

        root.Parent.enable.set(False)
        root.Parent.enable.set(True)

        assert wait_until(lambda: root.Parent.enable_events == [False, True])

        parent_calls = [entry for entry in block_calls if "root.Parent.RemoteCfg" in entry[0]]
        assert parent_calls == [
            ("root.Parent.RemoteCfg", False),
            ("root.Parent.RemoteCfg", True),
        ]
        assert any("root.Parent.Child.ChildRemote" in path for path, _ in block_calls)


def test_root_save_lists_address_map_and_yaml_application(tmp_path, monkeypatch):
    with StructureRoot() as root:
        variable_list = tmp_path / "vars.txt"
        address_map = tmp_path / "addr.txt"
        first_yaml = tmp_path / "first.yml"
        second_yaml = tmp_path / "second.yml"

        root.saveVariableList(str(variable_list), polledOnly=True, incGroups="Cfg")
        root.saveAddressMap(str(address_map))

        first_yaml.write_text("root.Parent:\n  ConfigValue: 11\n")
        second_yaml.write_text("root.Parent:\n  PolledValue: 12\n")

        write_calls = []
        monkeypatch.setattr(root, "_write", lambda: write_calls.append("write") or True)

        root.InitAfterConfig.set(True)
        root.loadYaml(
            name=f"{first_yaml},{second_yaml}",
            writeEach=False,
            modes=["RW"],
            incGroups="Cfg",
        )

        assert root.Parent.ConfigValue.value() == 11
        assert root.Parent.PolledValue.value() == 12
        assert write_calls == ["write"]
        assert root.initialize_calls == 1

        variable_text = variable_list.read_text()
        assert "root.Parent.PolledValue" in variable_text
        assert "root.Parent.ConfigValue" not in variable_text
        assert "root.Parent.StatusValue" not in variable_text

        address_text = address_map.read_text()
        assert "root.Parent.RemoteCfg" in address_text
        assert "root.Parent.ConfigValue" not in address_text


def test_root_set_yaml_invalid_entry_and_tree_yaml_properties(monkeypatch):
    errors = []

    with StructureRoot() as root:
        monkeypatch.setattr(root._log, "error", lambda msg, key: errors.append((msg, key)))
        monkeypatch.setattr(root, "_write", lambda: True)

        root.setYaml(
            yml="root.Parent:\n  ConfigValue: 21\nmissing.path:\n  Value: 1\n",
            writeEach=False,
            modes=["RW"],
        )

        assert root.Parent.ConfigValue.value() == 21
        assert errors == [("Entry %s not found", "missing.path")]

        tree = root.Parent._getDict(modes=["RW"], incGroups="Cfg", excGroups=None, properties=False)
        assert tree["ConfigValue"].value == 21

        yaml_text = pr.dataToYaml({"root": {"Parent": tree}})
        assert "ConfigValue: 21" in yaml_text
        assert "alarmStatus" not in yaml_text


def test_command_disabled_and_helper_verification_paths():
    with StructureRoot() as root:
        root.enable.set(False)
        assert root.DoThing(7) is None
        assert root.command_args == []

    fake = FakeCommandTarget(read_back=2)

    pr.BaseCommand.createToggle((1, 3))(fake)
    pr.BaseCommand.createTouch(5)(fake)
    pr.BaseCommand.touch(fake, None)
    pr.BaseCommand.touchZero(fake)
    pr.BaseCommand.touchOne(fake)
    pr.BaseCommand.createPostedTouch(9)(fake)
    pr.BaseCommand.postedTouch(fake, 11)
    pr.BaseCommand.postedTouchZero(fake)
    pr.BaseCommand.postedTouchOne(fake)

    assert fake.set_calls == [1, 3, 5, 1, 0, 1]
    assert fake.post_calls == [9, 11, 0, 1]

    with pytest.raises(pr.CommandError, match="Verification failed"):
        pr.BaseCommand.setAndVerifyArg(fake, 4)


def test_variable_listener_add_remove_and_call_disp(wait_until):
    disp_updates = []

    with StructureRoot() as root:
        root.HexValue._addListenerCpp(lambda path, value: disp_updates.append((path, value)))
        root.HexValue.set(47)
        assert wait_until(lambda: disp_updates == [("root.HexValue", "0x2f")])
        assert root.FmtCmd.callDisp() == "255"

        called = []
        def listener(path, value):
            called.append((path, value.value))

        root.Parent.ConfigValue.addListener(listener)
        root.Parent.ConfigValue.addListener(listener)
        root.Parent.ConfigValue.set(22)
        assert wait_until(lambda: called == [("root.Parent.ConfigValue", 22)])

        root.Parent.ConfigValue.delListener(listener)
        root.Parent.ConfigValue.set(23)
        root.waitOnUpdate()
        assert called == [("root.Parent.ConfigValue", 22)]
