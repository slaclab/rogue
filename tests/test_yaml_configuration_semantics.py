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
import rogue.interfaces.memory


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


class YamlConfigRoot(pr.Root):
    def __init__(self):
        super().__init__(name="root", pollEn=False)
        self._mem = rogue.interfaces.memory.Emulate(4, 0x4000)
        self.addInterface(self._mem)
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
