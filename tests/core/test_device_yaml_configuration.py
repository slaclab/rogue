#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import zipfile

import pyrogue as pr
from conftest import MemoryRoot


class InnerDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add(pr.LocalVariable(name="InnerLocal", value=0))
        self.add(pr.RemoteVariable(
            name="InnerRemote",
            offset=0x0,
            bitSize=8,
            base=pr.UInt,
            mode="RW",
        ))


class OuterDevice(pr.Device):
    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, **kwargs)
        self.add(pr.LocalVariable(name="OuterLocal", value="init"))
        self.add(pr.RemoteVariable(
            name="OuterRemote",
            offset=0x0,
            bitSize=8,
            base=pr.UInt,
            mode="RW",
        ))
        self.add(InnerDevice(name="Inner", offset=0x100))


class DeviceYamlRoot(MemoryRoot):
    def __init__(self):
        super().__init__(name="root")
        self.add(OuterDevice(name="Outer", offset=0x000, mem_base=self._mem))


class ParentWithArrayChildren(pr.Device):
    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, **kwargs)
        self.add(InnerDevice(name="Ch[0]", offset=0x000))
        self.add(InnerDevice(name="Ch[1]", offset=0x100))
        self.add(InnerDevice(name="Ch[2]", offset=0x200))


class ArrayDeviceYamlRoot(MemoryRoot):
    def __init__(self):
        super().__init__(name="root")
        self.add(OuterDevice(name="Dev[0]", offset=0x000, mem_base=self._mem))
        self.add(OuterDevice(name="Dev[1]", offset=0x800, mem_base=self._mem))
        self.add(OuterDevice(name="Dev[2]", offset=0x1000, mem_base=self._mem))
        self.add(ParentWithArrayChildren(name="Parent", offset=0x2000, mem_base=self._mem))


# --- Device-level saveYaml ---

def test_device_save_yaml_produces_device_relative_output(tmp_path):
    with DeviceYamlRoot() as root:
        root.Outer.OuterRemote.set(42)
        root.Outer.Inner.InnerLocal.set(7)

        out = tmp_path / "outer_config.yml"
        root.Outer.saveYaml(name=str(out), readFirst=False, modes=["RW"])

        data = pr.yamlToData(fName=str(out))
        assert "Outer" in data
        assert data["Outer"]["OuterRemote"] == 0x2A
        assert data["Outer"]["Inner"]["InnerLocal"] == 7


# --- Device-level loadYaml ---

def test_device_load_yaml_with_device_name_as_top_key(tmp_path):
    config = tmp_path / "config.yml"
    config.write_text(
        "Outer:\n"
        "  OuterRemote: 10\n"
        "  Inner:\n"
        "    InnerLocal: 99\n"
    )

    with DeviceYamlRoot() as root:
        root.Outer.loadYaml(name=str(config), writeEach=False, modes=["RW"])

        assert root.Outer.OuterRemote.value() == 10
        assert root.Outer.Inner.InnerLocal.value() == 99


def test_device_load_yaml_with_child_names_as_top_keys(tmp_path):
    config = tmp_path / "config.yml"
    config.write_text(
        "OuterRemote: 15\n"
        "Inner:\n"
        "  InnerLocal: 33\n"
    )

    with DeviceYamlRoot() as root:
        root.Outer.loadYaml(name=str(config), writeEach=False, modes=["RW"])

        assert root.Outer.OuterRemote.value() == 15
        assert root.Outer.Inner.InnerLocal.value() == 33


def test_device_load_yaml_on_inner_device(tmp_path):
    config = tmp_path / "inner_config.yml"
    config.write_text(
        "Inner:\n"
        "  InnerLocal: 42\n"
        "  InnerRemote: 7\n"
    )

    with DeviceYamlRoot() as root:
        root.Outer.Inner.loadYaml(name=str(config), writeEach=False, modes=["RW"])

        assert root.Outer.Inner.InnerLocal.value() == 42
        assert root.Outer.Inner.InnerRemote.value() == 7


# --- Device-level setYaml ---

def test_device_set_yaml_with_device_relative_paths():
    with DeviceYamlRoot() as root:
        root.Outer.setYaml(
            yml=(
                "Outer:\n"
                "  OuterRemote: 20\n"
                "  Inner:\n"
                "    InnerLocal: 55\n"
            ),
            writeEach=False,
            modes=["RW"],
        )

        assert root.Outer.OuterRemote.value() == 20
        assert root.Outer.Inner.InnerLocal.value() == 55


def test_device_set_yaml_with_child_keys():
    with DeviceYamlRoot() as root:
        root.Outer.setYaml(
            yml=(
                "OuterLocal: changed\n"
                "Inner:\n"
                "  InnerRemote: 3\n"
            ),
            writeEach=False,
            modes=["RW"],
        )

        assert root.Outer.OuterLocal.value() == "changed"
        assert root.Outer.Inner.InnerRemote.value() == 3


# --- Save/Load round-trip ---

def test_device_save_load_round_trip(tmp_path):
    out = tmp_path / "round_trip.yml"

    with DeviceYamlRoot() as root:
        root.Outer.OuterRemote.set(17)
        root.Outer.Inner.InnerLocal.set(88)

        root.Outer.saveYaml(name=str(out), readFirst=False, modes=["RW"])

        root.Outer.OuterRemote.set(0)
        root.Outer.Inner.InnerLocal.set(0)

        root.Outer.loadYaml(name=str(out), writeEach=False, modes=["RW"])

        assert root.Outer.OuterRemote.value() == 17
        assert root.Outer.Inner.InnerLocal.value() == 88


# --- Scoped write ---

def test_device_load_yaml_scoped_write(tmp_path, monkeypatch):
    config = tmp_path / "config.yml"
    config.write_text("Inner:\n  InnerLocal: 5\n")

    with DeviceYamlRoot() as root:
        device_writes = []

        orig_write_blocks = root.Outer.writeBlocks

        def recording_device_write(**kwargs):
            device_writes.append(kwargs)
            return orig_write_blocks(**kwargs)

        monkeypatch.setattr(root.Outer, "writeBlocks", recording_device_write)

        root.Outer.loadYaml(name=str(config), writeEach=False, modes=["RW"])

        assert root.Outer.Inner.InnerLocal.value() == 5
        assert len(device_writes) > 0


# --- ForceWrite ---

def test_device_load_yaml_respects_force_write(tmp_path, monkeypatch):
    config = tmp_path / "config.yml"
    config.write_text("Inner:\n  InnerLocal: 9\n")

    with DeviceYamlRoot() as root:
        force_values = []

        orig_write_blocks = root.Outer.writeBlocks

        def recording_write(**kwargs):
            force_values.append(kwargs.get("force", False))
            return orig_write_blocks(**kwargs)

        monkeypatch.setattr(root.Outer, "writeBlocks", recording_write)

        root.ForceWrite.set(True)
        root.Outer.loadYaml(name=str(config), writeEach=False, modes=["RW"])

        assert any(f is True for f in force_values)


# --- Device SaveConfig/LoadConfig commands ---

def test_device_save_yaml_load_yaml_methods(tmp_path):
    out = tmp_path / "dev_config.yml"

    with DeviceYamlRoot() as root:
        root.Outer.OuterRemote.set(12)
        root.Outer.Inner.InnerLocal.set(34)

        root.Outer.saveYaml(name=str(out), readFirst=False, modes=["RW"])

        root.Outer.OuterRemote.set(0)
        root.Outer.Inner.InnerLocal.set(0)

        root.Outer.loadYaml(name=str(out), writeEach=False, modes=["RW"])

        assert root.Outer.OuterRemote.value() == 12
        assert root.Outer.Inner.InnerLocal.value() == 34


# --- writeEach=True ---

def test_device_set_yaml_write_each_true(monkeypatch):
    with DeviceYamlRoot() as root:
        immediate_writes = []
        staged_writes = []

        original_set_disp = root.Outer.OuterRemote.setDisp

        def recording_set_disp(s_value, write=True, index=-1):
            if write:
                immediate_writes.append(s_value)
            else:
                staged_writes.append(s_value)
            return original_set_disp(s_value, write=write, index=index)

        monkeypatch.setattr(root.Outer.OuterRemote, "setDisp", recording_set_disp)

        root.Outer.setYaml(
            yml="OuterRemote: 8\n",
            writeEach=True,
            modes=["RW"],
        )

        assert immediate_writes == [8]
        assert staged_writes == []


# --- Array device wildcards ---

def test_device_load_yaml_with_array_wildcards_on_device(tmp_path):
    config = tmp_path / "config.yml"
    config.write_text(
        "Ch[*]:\n"
        "  InnerLocal: 42\n"
    )

    with ArrayDeviceYamlRoot() as root:
        root.Parent.loadYaml(name=str(config), writeEach=False, modes=["RW"])

        for idx in range(3):
            assert root.Parent.Ch[idx].InnerLocal.value() == 42


def test_device_set_yaml_with_array_slice_on_device():
    with ArrayDeviceYamlRoot() as root:
        root.Parent.setYaml(
            yml=(
                "Ch[1:3]:\n"
                "  InnerLocal: 99\n"
            ),
            writeEach=False,
            modes=["RW"],
        )

        assert root.Parent.Ch[0].InnerLocal.value() == 0
        assert root.Parent.Ch[1].InnerLocal.value() == 99
        assert root.Parent.Ch[2].InnerLocal.value() == 99


def test_device_set_yaml_with_array_wildcards_at_root():
    with ArrayDeviceYamlRoot() as root:
        root.setYaml(
            yml=(
                "root:\n"
                "  Dev[*]:\n"
                "    OuterLocal: broadcast\n"
            ),
            writeEach=False,
            modes=["RW"],
        )

        for idx in range(3):
            assert root.Dev[idx].OuterLocal.value() == "broadcast"


def test_device_set_yaml_with_array_slice_at_root():
    with ArrayDeviceYamlRoot() as root:
        root.setYaml(
            yml=(
                "root:\n"
                "  Dev[1:3]:\n"
                "    OuterLocal: sliced\n"
            ),
            writeEach=False,
            modes=["RW"],
        )

        assert root.Dev[0].OuterLocal.value() == "init"
        assert root.Dev[1].OuterLocal.value() == "sliced"
        assert root.Dev[2].OuterLocal.value() == "sliced"


# --- Directory sorted order ---

def test_device_load_yaml_directory_sorted_order(tmp_path):
    first = tmp_path / "00-defaults.yml"
    second = tmp_path / "10-overrides.yml"

    first.write_text("OuterLocal: base\n")
    second.write_text("OuterLocal: override\n")

    with DeviceYamlRoot() as root:
        root.Outer.loadYaml(name=str(tmp_path), writeEach=False, modes=["RW"])

        assert root.Outer.OuterLocal.value() == "override"


# --- Zip support ---

def test_device_load_yaml_zip_support(tmp_path):
    archive = tmp_path / "configs.zip"

    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_LZMA) as zf:
        zf.writestr("cfg/config.yml", "OuterRemote: 25\nInner:\n  InnerLocal: 77\n")

    with DeviceYamlRoot() as root:
        root.Outer.loadYaml(name=f"{archive}/cfg", writeEach=False, modes=["RW"])

        assert root.Outer.OuterRemote.value() == 25
        assert root.Outer.Inner.InnerLocal.value() == 77


# --- Invalid entry ---

def test_device_load_yaml_invalid_entry_logs_error(tmp_path, monkeypatch):
    config = tmp_path / "bad.yml"
    config.write_text("NonExistent:\n  Foo: 1\n")

    with DeviceYamlRoot() as root:
        errors = []
        monkeypatch.setattr(root.Outer._log, "error", lambda msg, key: errors.append((msg, key)))

        root.Outer.loadYaml(name=str(config), writeEach=False, modes=["RW"])

        assert len(errors) > 0
        assert errors[0] == ("Entry %s not found", "NonExistent")


# --- Root backward compat ---

def test_root_load_yaml_still_uses_absolute_paths(tmp_path):
    config = tmp_path / "config.yml"
    config.write_text(
        "root.Outer:\n"
        "  OuterRemote: 7\n"
        "root.Outer.Inner:\n"
        "  InnerLocal: 14\n"
    )

    with DeviceYamlRoot() as root:
        root.loadYaml(name=str(config), writeEach=False, modes=["RW"])

        assert root.Outer.OuterRemote.value() == 7
        assert root.Outer.Inner.InnerLocal.value() == 14


def test_root_load_yaml_init_after_config(tmp_path, monkeypatch):
    config = tmp_path / "config.yml"
    config.write_text("root.Outer:\n  OuterLocal: test\n")

    with DeviceYamlRoot() as root:
        init_calls = []
        monkeypatch.setattr(root, "initialize", lambda: init_calls.append(1))
        monkeypatch.setattr(root, "_write", lambda: True)

        root.InitAfterConfig.set(True)
        root.loadYaml(name=str(config), writeEach=False, modes=["RW"])

        assert root.Outer.OuterLocal.value() == "test"
        assert init_calls == [1]


def test_root_set_yaml_init_after_config(monkeypatch):
    with DeviceYamlRoot() as root:
        init_calls = []
        monkeypatch.setattr(root, "initialize", lambda: init_calls.append(1))
        monkeypatch.setattr(root, "_write", lambda: True)

        root.InitAfterConfig.set(True)
        root.setYaml(
            yml="root.Outer:\n  OuterLocal: from_yaml\n",
            writeEach=False,
            modes=["RW"],
        )

        assert root.Outer.OuterLocal.value() == "from_yaml"
        assert init_calls == [1]


def test_root_save_config_load_config_commands_still_work(tmp_path):
    config_out = tmp_path / "root_config.yml"

    with DeviceYamlRoot() as root:
        root.Outer.OuterRemote.set(19)
        root.SaveConfig(str(config_out))

        root.Outer.OuterRemote.set(0)
        root.LoadConfig(str(config_out))

        assert root.Outer.OuterRemote.value() == 19
