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
from conftest import MemoryRoot


class ConfigChild(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add(pr.LocalVariable(name="ChildValue", value="child_init"))


class ConfigLeaf(pr.Device):
    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, **kwargs)
        self.add(pr.LocalVariable(name="SomeValue", value="init"))
        self.add(ConfigChild(name="Child", offset=0x100))


class YamlConfigRoot(MemoryRoot):
    def __init__(self):
        super().__init__(name="root")
        self.initialize_calls = 0
        self.add(ConfigLeaf(name="SomeDeviceArray[0]", offset=0x000, mem_base=self._mem))
        self.add(ConfigLeaf(name="SomeDeviceArray[1]", offset=0x100, mem_base=self._mem))
        self.add(ConfigLeaf(name="SomeDeviceArray[2]", offset=0x200, mem_base=self._mem))

    def initialize(self):
        self.initialize_calls += 1
        super().initialize()


def test_root_load_yaml_still_resolves_absolute_paths(tmp_path):
    config = tmp_path / "config.yml"
    config.write_text(
        "root.SomeDeviceArray[0]:\n"
        "  SomeValue: from_file\n"
        "root.SomeDeviceArray[1].Child:\n"
        "  ChildValue: child_from_file\n"
    )

    with YamlConfigRoot() as root:
        root.loadYaml(name=str(config), writeEach=False, modes=["RW"])

        assert root.SomeDeviceArray[0].SomeValue.value() == "from_file"
        assert root.SomeDeviceArray[1].Child.ChildValue.value() == "child_from_file"
        assert root.SomeDeviceArray[2].SomeValue.value() == "init"


def test_root_set_yaml_still_resolves_absolute_paths(monkeypatch):
    with YamlConfigRoot() as root:
        monkeypatch.setattr(root, "_write", lambda: True)

        root.setYaml(
            yml=(
                "root.SomeDeviceArray[0]:\n"
                "  SomeValue: from_text\n"
                "root.SomeDeviceArray[1].Child:\n"
                "  ChildValue: child_from_text\n"
            ),
            writeEach=False,
            modes=["RW"],
        )

        assert root.SomeDeviceArray[0].SomeValue.value() == "from_text"
        assert root.SomeDeviceArray[1].Child.ChildValue.value() == "child_from_text"
        assert root.SomeDeviceArray[2].SomeValue.value() == "init"


def test_root_set_yaml_accepts_root_name_as_top_key(monkeypatch):
    with YamlConfigRoot() as root:
        monkeypatch.setattr(root, "_write", lambda: True)

        root.setYaml(
            yml=(
                "root:\n"
                "  SomeDeviceArray[0]:\n"
                "    SomeValue: from_root_key\n"
                "  SomeDeviceArray[1]:\n"
                "    Child:\n"
                "      ChildValue: child_from_root_key\n"
            ),
            writeEach=False,
            modes=["RW"],
        )

        assert root.SomeDeviceArray[0].SomeValue.value() == "from_root_key"
        assert root.SomeDeviceArray[1].Child.ChildValue.value() == "child_from_root_key"
        assert root.SomeDeviceArray[2].SomeValue.value() == "init"


def test_root_load_yaml_resolves_include_under_root_name(tmp_path):
    child = tmp_path / "child.yml"
    parent = tmp_path / "parent.yml"

    child.write_text(
        "SomeDeviceArray[1]:\n"
        "  SomeValue: included\n"
        "  Child:\n"
        "    ChildValue: child_included\n"
    )
    parent.write_text(
        "root: !include child.yml\n"
    )

    with YamlConfigRoot() as root:
        root.loadYaml(name=str(parent), writeEach=False, modes=["RW"])

        assert root.SomeDeviceArray[0].SomeValue.value() == "init"
        assert root.SomeDeviceArray[1].SomeValue.value() == "included"
        assert root.SomeDeviceArray[1].Child.ChildValue.value() == "child_included"
        assert root.SomeDeviceArray[2].SomeValue.value() == "init"


def test_root_set_yaml_init_after_config(monkeypatch):
    with YamlConfigRoot() as root:
        monkeypatch.setattr(root, "_write", lambda: True)

        root.InitAfterConfig.set(True)
        root.setYaml(
            yml=(
                "root.SomeDeviceArray[0]:\n"
                "  SomeValue: from_text\n"
            ),
            writeEach=False,
            modes=["RW"],
        )

        assert root.SomeDeviceArray[0].SomeValue.value() == "from_text"
        assert root.initialize_calls == 1
