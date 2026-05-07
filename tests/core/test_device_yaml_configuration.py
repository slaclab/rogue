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
        self.add(pr.LocalVariable(name="InnerLocal", value=0, groups=["Cfg"]))
        self.add(pr.RemoteVariable(
            name="InnerRemote",
            offset=0x0,
            bitSize=8,
            base=pr.UInt,
            mode="RW",
            groups=["Hw"],
        ))
        self.add(pr.RemoteVariable(
            name="InnerArray",
            offset=0x4,
            numValues=4,
            valueBits=8,
            valueStride=8,
            base=pr.UInt,
            mode="RW",
            groups=["Cfg"],
        ))


class OuterDevice(pr.Device):
    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, **kwargs)
        self.add(pr.LocalVariable(name="OuterLocal", value="init", groups=["Cfg"]))
        self.add(pr.RemoteVariable(
            name="OuterRemote",
            offset=0x0,
            bitSize=8,
            base=pr.UInt,
            mode="RW",
            groups=["Hw"],
        ))
        self.add(InnerDevice(name="Inner", offset=0x100, groups=["Cfg"]))


class DeviceYamlRoot(MemoryRoot):
    def __init__(self):
        super().__init__(name="root")
        self.add(OuterDevice(name="Outer", offset=0x000, mem_base=self._mem))


class ParentWithArrayChildren(pr.Device):
    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, **kwargs)
        self.add(InnerDevice(name="Ch[0]", offset=0x000, groups=["Cfg"]))
        self.add(InnerDevice(name="Ch[1]", offset=0x100, groups=["Cfg"]))
        self.add(InnerDevice(name="Ch[2]", offset=0x200, groups=["Cfg"]))


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


def test_device_save_yaml_filters_groups(tmp_path):
    with DeviceYamlRoot() as root:
        root.Outer.OuterLocal.set("cfg")
        root.Outer.OuterRemote.set(42)
        root.Outer.Inner.InnerLocal.set(7)
        root.Outer.Inner.InnerRemote.set(9)

        out = tmp_path / "outer_cfg.yml"
        root.Outer.saveYaml(
            name=str(out),
            readFirst=False,
            modes=["RW"],
            incGroups=["Cfg", "Hw"],
            excGroups="Hw",
        )

        data = pr.yamlToData(fName=str(out))
        assert data["Outer"]["OuterLocal"] == "cfg"
        assert data["Outer"]["Inner"]["InnerLocal"] == 7
        assert "OuterRemote" not in data["Outer"]
        assert "InnerRemote" not in data["Outer"]["Inner"]


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


def test_device_load_yaml_accepts_list_input_in_order(tmp_path):
    first = tmp_path / "first.yml"
    second = tmp_path / "second.yml"

    first.write_text(
        "OuterLocal: first\n"
        "Inner:\n"
        "  InnerLocal: 11\n"
    )
    second.write_text(
        "OuterLocal: second\n"
    )

    with DeviceYamlRoot() as root:
        root.Outer.loadYaml(name=[str(first), str(second)], writeEach=False, modes=["RW"])

        assert root.Outer.OuterLocal.value() == "second"
        assert root.Outer.Inner.InnerLocal.value() == 11


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


def test_device_set_yaml_filters_groups():
    with DeviceYamlRoot() as root:
        root.Outer.setYaml(
            yml=(
                "OuterLocal: changed\n"
                "OuterRemote: 22\n"
                "Inner:\n"
                "  InnerLocal: 33\n"
                "  InnerRemote: 44\n"
            ),
            writeEach=False,
            modes=["RW"],
            incGroups=["Cfg", "Hw"],
            excGroups="Hw",
        )

        assert root.Outer.OuterLocal.value() == "changed"
        assert root.Outer.Inner.InnerLocal.value() == 33
        assert root.Outer.OuterRemote.value() == 0
        assert root.Outer.Inner.InnerRemote.value() == 0


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


def test_device_load_yaml_write_each_true_skips_bulk_commit(tmp_path, monkeypatch):
    config = tmp_path / "config.yml"
    config.write_text("OuterRemote: 8\n")

    with DeviceYamlRoot() as root:
        immediate_writes = []
        bulk_commits = []

        original_set_disp = root.Outer.OuterRemote.setDisp

        def recording_set_disp(s_value, write=True, index=-1):
            if write:
                immediate_writes.append(s_value)
            return original_set_disp(s_value, write=write, index=index)

        monkeypatch.setattr(root.Outer.OuterRemote, "setDisp", recording_set_disp)
        monkeypatch.setattr(root.Outer, "_writeConfig", lambda: bulk_commits.append("write") or True)

        root.Outer.loadYaml(name=str(config), writeEach=True, modes=["RW"])

        assert immediate_writes == [8]
        assert bulk_commits == []


# --- writeEach ---

def test_device_set_yaml_write_each_controls_immediate_writes(monkeypatch):
    with ArrayDeviceYamlRoot() as root:
        staged_writes = []
        immediate_writes = []
        bulk_commits = []

        original_set_disp = root.Parent.Ch[0].InnerArray.setDisp

        def recording_set_disp(s_value, write=True, index=-1):
            if write:
                immediate_writes.append(index)
            else:
                staged_writes.append(index)
            return original_set_disp(s_value, write=write, index=index)

        monkeypatch.setattr(root.Parent.Ch[0].InnerArray, "setDisp", recording_set_disp)
        monkeypatch.setattr(root.Parent, "_writeConfig", lambda: bulk_commits.append("write") or True)

        root.Parent.setYaml(
            yml=(
                "Ch[0]:\n"
                "  InnerArray[1:3]: 4\n"
            ),
            writeEach=False,
            modes=["RW"],
        )

        assert staged_writes == [1, 2]
        assert immediate_writes == []
        assert bulk_commits == ["write"]

        staged_writes.clear()
        immediate_writes.clear()
        bulk_commits.clear()

        root.Parent.setYaml(
            yml=(
                "Ch[0]:\n"
                "  InnerArray[1:3]: 6\n"
            ),
            writeEach=True,
            modes=["RW"],
        )

        assert staged_writes == []
        assert immediate_writes == [1, 2]
        assert bulk_commits == []


# --- Array device wildcards ---

def test_device_load_yaml_with_array_wildcards_on_device(tmp_path):
    config = tmp_path / "config.yml"
    config.write_text(
        "Ch[:]:\n"
        "  InnerLocal: 42\n"
        "  InnerArray[:]: 3\n"
    )

    with ArrayDeviceYamlRoot() as root:
        root.Parent.loadYaml(name=str(config), writeEach=False, modes=["RW"])

        for idx in range(3):
            assert root.Parent.Ch[idx].InnerLocal.value() == 42
            assert list(root.Parent.Ch[idx].InnerArray.value()) == [3, 3, 3, 3]


def test_device_set_yaml_supports_array_variable_wildcards_and_scalar_slices():
    with ArrayDeviceYamlRoot() as root:
        root.Parent.setYaml(
            yml=(
                "Ch[0]:\n"
                "  InnerArray[*]: 5\n"
                "  InnerArray[1:3]: 7\n"
            ),
            writeEach=False,
            modes=["RW"],
        )

        assert list(root.Parent.Ch[0].InnerArray.value()) == [5, 7, 7, 5]

        root.Parent.setYaml(
            yml=(
                "Ch[0]:\n"
                "  InnerArray[:]: 9\n"
            ),
            writeEach=False,
            modes=["RW"],
        )

        # [:] is equivalent to [*]
        assert list(root.Parent.Ch[0].InnerArray.value()) == [9, 9, 9, 9]


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


def test_device_set_yaml_recursively_applies_wildcards_to_array_variables():
    with ArrayDeviceYamlRoot() as root:
        root.Parent.setYaml(
            yml=(
                "Ch[*]:\n"
                "  InnerLocal: 44\n"
                "  InnerArray[1:3]: 4\n"
            ),
            writeEach=False,
            modes=["RW"],
        )

        for idx in range(3):
            assert root.Parent.Ch[idx].InnerLocal.value() == 44
            assert list(root.Parent.Ch[idx].InnerArray.value()) == [0, 4, 4, 0]


# --- Directory sorted order ---

def test_device_load_yaml_directory_sorted_order(tmp_path):
    first = tmp_path / "00-defaults.yml"
    second = tmp_path / "10-overrides.yml"

    first.write_text(
        "Ch[:]:\n"
        "  InnerLocal: 10\n"
        "  InnerArray[*]: 1\n"
    )
    second.write_text(
        "Ch[1]:\n"
        "  InnerLocal: 20\n"
        "  InnerArray[2]: 9\n"
    )

    with ArrayDeviceYamlRoot() as root:
        root.Parent.loadYaml(name=str(tmp_path), writeEach=False, modes=["RW"])

        assert root.Parent.Ch[0].InnerLocal.value() == 10
        assert root.Parent.Ch[1].InnerLocal.value() == 20
        assert root.Parent.Ch[2].InnerLocal.value() == 10
        assert list(root.Parent.Ch[0].InnerArray.value()) == [1, 1, 1, 1]
        assert list(root.Parent.Ch[1].InnerArray.value()) == [1, 1, 9, 1]


def test_device_load_yaml_filters_groups(tmp_path):
    config = tmp_path / "config.yml"
    config.write_text(
        "OuterLocal: loaded\n"
        "OuterRemote: 22\n"
        "Inner:\n"
        "  InnerLocal: 33\n"
        "  InnerRemote: 44\n"
    )

    with DeviceYamlRoot() as root:
        root.Outer.loadYaml(
            name=str(config),
            writeEach=False,
            modes=["RW"],
            incGroups=["Cfg", "Hw"],
            excGroups="Hw",
        )

        assert root.Outer.OuterLocal.value() == "loaded"
        assert root.Outer.Inner.InnerLocal.value() == 33
        assert root.Outer.OuterRemote.value() == 0
        assert root.Outer.Inner.InnerRemote.value() == 0


def test_device_load_yaml_resolves_relative_include(tmp_path):
    child = tmp_path / "child.yml"
    parent = tmp_path / "parent.yml"

    child.write_text(
        "Ch[1]:\n"
        "  InnerLocal: 61\n"
        "  InnerArray[:]: 8\n"
    )
    parent.write_text(
        "Parent: !include child.yml\n"
    )

    with ArrayDeviceYamlRoot() as root:
        root.Parent.loadYaml(name=str(parent), writeEach=False, modes=["RW"])

        assert root.Parent.Ch[0].InnerLocal.value() == 0
        assert root.Parent.Ch[1].InnerLocal.value() == 61
        assert root.Parent.Ch[2].InnerLocal.value() == 0
        assert list(root.Parent.Ch[1].InnerArray.value()) == [8, 8, 8, 8]


# --- Zip support ---

def test_device_load_yaml_zip_support(tmp_path):
    archive = tmp_path / "configs.zip"

    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_LZMA) as zf:
        # Override written first; load order is sorted names, not insertion order.
        zf.writestr("cfg/10-overrides.yml", "OuterRemote: 25\n")
        zf.writestr("cfg/00-defaults.yml", "OuterRemote: 12\nInner:\n  InnerLocal: 77\n")

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
