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
import zipfile
from conftest import MemoryRoot


class ConfigLeaf(pr.Device):
    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, **kwargs)
        self.add(pr.LocalVariable(name="SomeValue", value="init"))
        self.add(pr.RemoteVariable(
            name="SomeArrayValue",
            offset=0x0,
            numValues=4,
            valueBits=8,
            valueStride=8,
            base=pr.UInt,
            mode="RW",
        ))


class YamlConfigRoot(MemoryRoot):
    def __init__(self):
        super().__init__(name="root")
        self.add(ConfigLeaf(name="SomeDeviceArray[0]", offset=0x000, mem_base=self._mem))
        self.add(ConfigLeaf(name="SomeDeviceArray[1]", offset=0x100, mem_base=self._mem))
        self.add(ConfigLeaf(name="SomeDeviceArray[2]", offset=0x200, mem_base=self._mem))


def test_set_yaml_supports_array_variable_wildcards_and_scalar_slices():
    with YamlConfigRoot() as root:
        root.setYaml(
            yml=(
                "root:\n"
                "  SomeDeviceArray[0]:\n"
                "    SomeArrayValue[*]: 5\n"
                "    SomeArrayValue[1:3]: 7\n"
            ),
            writeEach=False,
            modes=["RW"],
        )

        # Wildcard writes broadcast across the whole array.
        assert list(root.SomeDeviceArray[0].SomeArrayValue.value()) == [5, 7, 7, 5]

        root.setYaml(
            yml=(
                "root:\n"
                "  SomeDeviceArray[0]:\n"
                "    SomeArrayValue[:]: 9\n"
            ),
            writeEach=False,
            modes=["RW"],
        )

        # ``[:]`` is the same all-elements selection as ``[*]``.
        assert list(root.SomeDeviceArray[0].SomeArrayValue.value()) == [9, 9, 9, 9]


def test_set_yaml_recursively_applies_wildcards_and_slices_to_device_arrays():
    with YamlConfigRoot() as root:
        root.setYaml(
            yml=(
                "root:\n"
                "  SomeDeviceArray[*]:\n"
                "    SomeValue: abcd\n"
                "    SomeArrayValue[1:3]: 4\n"
            ),
            writeEach=False,
            modes=["RW"],
        )

        # Device-array wildcards recurse into every matched subtree.
        for idx in range(3):
            assert root.SomeDeviceArray[idx].SomeValue.value() == "abcd"
            assert list(root.SomeDeviceArray[idx].SomeArrayValue.value()) == [0, 4, 4, 0]

        root.setYaml(
            yml=(
                "root:\n"
                "  SomeDeviceArray[1:3]:\n"
                "    SomeValue: slice\n"
            ),
            writeEach=False,
            modes=["RW"],
        )

        assert root.SomeDeviceArray[0].SomeValue.value() == "abcd"
        assert root.SomeDeviceArray[1].SomeValue.value() == "slice"
        assert root.SomeDeviceArray[2].SomeValue.value() == "slice"


def test_load_yaml_supports_recursive_colon_wildcards(tmp_path):
    config = tmp_path / "config.yml"
    config.write_text(
        "root:\n"
        "  SomeDeviceArray[:]:\n"
        "    SomeValue: from_file\n"
        "    SomeArrayValue[:]: 3\n"
    )

    with YamlConfigRoot() as root:
        root.loadYaml(name=str(config), writeEach=False, modes=["RW"])

        for idx in range(3):
            assert root.SomeDeviceArray[idx].SomeValue.value() == "from_file"
            assert list(root.SomeDeviceArray[idx].SomeArrayValue.value()) == [3, 3, 3, 3]


def test_load_yaml_last_assignment_wins_in_sorted_directory_order(tmp_path):
    first = tmp_path / "00-defaults.yml"
    second = tmp_path / "10-overrides.yml"

    first.write_text(
        "root:\n"
        "  SomeDeviceArray[:]:\n"
        "    SomeValue: base\n"
        "    SomeArrayValue[*]: 1\n"
    )
    second.write_text(
        "root:\n"
        "  SomeDeviceArray[1]:\n"
        "    SomeValue: override\n"
        "    SomeArrayValue[2]: 9\n"
    )

    with YamlConfigRoot() as root:
        root.loadYaml(name=str(tmp_path), writeEach=False, modes=["RW"])

        # Directory loads are sorted, so later files override earlier staged values.
        assert root.SomeDeviceArray[0].SomeValue.value() == "base"
        assert root.SomeDeviceArray[1].SomeValue.value() == "override"
        assert root.SomeDeviceArray[2].SomeValue.value() == "base"
        assert list(root.SomeDeviceArray[0].SomeArrayValue.value()) == [1, 1, 1, 1]
        assert list(root.SomeDeviceArray[1].SomeArrayValue.value()) == [1, 1, 9, 1]


def test_load_yaml_resolves_relative_include_through_root_loader(tmp_path):
    child = tmp_path / "child.yml"
    parent = tmp_path / "parent.yml"

    child.write_text(
        "SomeDeviceArray[1]:\n"
        "  SomeValue: included\n"
        "  SomeArrayValue[:]: 8\n"
    )
    parent.write_text(
        "root: !include child.yml\n"
    )

    with YamlConfigRoot() as root:
        root.loadYaml(name=str(parent), writeEach=False, modes=["RW"])

        assert root.SomeDeviceArray[0].SomeValue.value() == "init"
        assert root.SomeDeviceArray[1].SomeValue.value() == "included"
        assert root.SomeDeviceArray[2].SomeValue.value() == "init"
        assert list(root.SomeDeviceArray[1].SomeArrayValue.value()) == [8, 8, 8, 8]


def test_load_yaml_sorts_zip_directory_members_lexicographically(tmp_path):
    archive = tmp_path / "configs.zip"

    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_LZMA) as zf:
        # Write the override first to prove load order follows sorted names,
        # not archive insertion order.
        zf.writestr(
            "cfg/10-overrides.yml",
            "root:\n"
            "  SomeDeviceArray[1]:\n"
            "    SomeValue: override\n",
        )
        zf.writestr(
            "cfg/00-defaults.yml",
            "root:\n"
            "  SomeDeviceArray[:]:\n"
            "    SomeValue: base\n",
        )

    with YamlConfigRoot() as root:
        root.loadYaml(name=f"{archive}/cfg", writeEach=False, modes=["RW"])

        assert root.SomeDeviceArray[0].SomeValue.value() == "base"
        assert root.SomeDeviceArray[1].SomeValue.value() == "override"
        assert root.SomeDeviceArray[2].SomeValue.value() == "base"


def test_set_yaml_write_each_controls_immediate_writes(monkeypatch):
    with YamlConfigRoot() as root:
        staged_writes = []
        immediate_writes = []
        bulk_commits = []

        original_set_disp = root.SomeDeviceArray[0].SomeArrayValue.setDisp

        def recording_set_disp(s_value, write=True, index=-1):
            if write:
                immediate_writes.append(index)
            else:
                staged_writes.append(index)
            return original_set_disp(s_value, write=write, index=index)

        monkeypatch.setattr(root.SomeDeviceArray[0].SomeArrayValue, "setDisp", recording_set_disp)
        monkeypatch.setattr(root, "_write", lambda: bulk_commits.append("write") or True)

        root.setYaml(
            yml=(
                "root:\n"
                "  SomeDeviceArray[0]:\n"
                "    SomeArrayValue[1:3]: 4\n"
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

        root.setYaml(
            yml=(
                "root:\n"
                "  SomeDeviceArray[0]:\n"
                "    SomeArrayValue[1:3]: 6\n"
            ),
            writeEach=True,
            modes=["RW"],
        )

        assert staged_writes == []
        assert immediate_writes == [1, 2]
        assert bulk_commits == []
