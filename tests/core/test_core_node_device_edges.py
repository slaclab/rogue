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
import pyrogue.interfaces as pr_interfaces
import pytest
import rogue.interfaces.memory


class ManagedInterface:
    def __init__(self):
        self.started = 0
        self.stopped = 0

    def _start(self):
        self.started += 1

    def _stop(self):
        self.stopped += 1


class RecursiveDevice(pr.Device):
    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, **kwargs)
        self.marker = []

        self.add(pr.LocalVariable(name="CfgValue", value=1, groups=["Cfg"]))
        self.add(pr.LocalVariable(name="StatusValue", value=2, mode="RO", groups=["Status"]))
        self.add(pr.RemoteVariable(
            name="RemoteWord",
            offset=0x0,
            bitSize=16,
            base=pr.UInt,
            mode="RW",
        ))

    def mark(self, token=None):
        self.marker.append(token)


class NodeEdgeRoot(pr.Root):
    def __init__(self):
        super().__init__(name="root", pollEn=False)
        self._mem = rogue.interfaces.memory.Emulate(4, 0x4000)
        self.addInterface(self._mem)

        self.managed = ManagedInterface()
        self.add(RecursiveDevice(name="Top", mem_base=self._mem))
        self.Top.addInterface(self.managed)
        self.Top.add(RecursiveDevice(name="Child", offset=0x100, mem_base=self._mem))
        self.Top.add(RecursiveDevice(name="Array[0]", offset=0x200, mem_base=self._mem))
        self.Top.add(RecursiveDevice(name="Array[1]", offset=0x300, mem_base=self._mem))


class RepeatedDevice(pr.Device):
    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, **kwargs)
        self.addRemoteVariables(
            name="RepeatedField",
            number=3,
            stride=4,
            offset=0x0,
            bitSize=8,
            base=pr.UInt,
            mode="RW",
        )


class RepeatedRoot(pr.Root):
    def __init__(self):
        super().__init__(name="root", pollEn=False)
        self._mem = rogue.interfaces.memory.Emulate(4, 0x4000)
        self.addInterface(self._mem)
        self.add(RepeatedDevice(name="Pack", mem_base=self._mem))


class ExposedNode(pr.Device):
    @property
    @pr.expose
    def exposed_prop(self):
        return "value"

    @pr.expose
    def exposed_method(self, arg, *, kw=None):
        return arg, kw


class ArrayLeaf(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add(pr.LocalVariable(name="LeafValue", value=kwargs["offset"]))


def test_add_remote_variables_pack_mode_exposes_all_alias():
    class PackedDevice(pr.Device):
        def __init__(self, mem_base, **kwargs):
            super().__init__(memBase=mem_base, **kwargs)
            self.addRemoteVariables(
                name="PackedField",
                number=3,
                stride=4,
                offset=0x0,
                bitSize=8,
                base=pr.UInt,
                mode="RW",
                pack=True,
            )

    class PackedRoot(pr.Root):
        def __init__(self):
            super().__init__(name="root", pollEn=False)
            self._mem = rogue.interfaces.memory.Emulate(4, 0x4000)
            self.addInterface(self._mem)
            self.add(PackedDevice(name="Pack", mem_base=self._mem))

    with PackedRoot() as root:
        assert sorted(root.Pack.PackedField.keys()) == [0, 1, 2]

        packed = root.Pack.PackedField_All
        packed.set("1_2_3", write=False)

        # The packed alias leaves the indexed array container at PackedField.
        assert root.Pack.PackedField[0].value() == 3
        assert root.Pack.PackedField[1].value() == 2
        assert root.Pack.PackedField[2].value() == 1
        assert packed.get(read=False) == "0x1_0x2_0x3"


def test_node_match_array_access_find_and_repr():
    with NodeEdgeRoot() as root:
        assert "root.Top" in repr(root.Top)
        assert root.Top.Array[0].path == "root.Top.Array[0]"

        nodes, keys = root.Top.nodeMatch("Array[1]")
        assert [node.path for node in nodes] == ["root.Top.Array[1]"]
        assert keys is None

        nodes, keys = root.Top.nodeMatch("Array[:]")
        assert sorted(node.path for node in nodes) == [
            "root.Top.Array[0]",
            "root.Top.Array[1]",
        ]
        assert keys is None

        nodes, keys = root.Top.nodeMatch("Array[*]")
        assert sorted(node.path for node in nodes) == [
            "root.Top.Array[0]",
            "root.Top.Array[1]",
        ]
        assert keys is None

        assert root.Top.node("Child") is root.Top.Child
        assert root.Top.node("Missing") is None
        assert root.Top.Array[1] in root.Top

        found = root.find(typ=pr.Device, name="Array\\[[01]\\]")
        assert sorted(node.path for node in found) == [
            "root.Top.Array[0]",
            "root.Top.Array[1]",
        ]

        direct_only = root.Top.find(recurse=False, typ=pr.Device)
        assert sorted(node.name for node in direct_only) == ["Array[0]", "Array[1]", "Child"]


def test_node_groups_dir_get_nodes_and_hidden_propagation():
    root = NodeEdgeRoot()
    root.Top.addToGroup("Shared")
    assert root.Top.Child.inGroup("Shared")
    assert root.Top.Array[0].inGroup("Shared")

    root.Top.removeFromGroup("Shared")
    assert root.Top.inGroup("Shared") is False

    assert "Child" in dir(root.Top)
    assert set(root.Top.variablesByGroup(incGroups="Cfg").keys()) == {"CfgValue"}
    assert set(root.Top.devicesByGroup().keys()) == {"Child", "Array[0]", "Array[1]"}
    assert set(root.Top.getNodes(pr.Device, excTyp=RecursiveDevice).keys()) == set()

    root.Top.hideVariables(True, variables=["CfgValue"])
    assert root.Top.CfgValue.hidden is True
    root.Top.hideVariables(False, variables=[root.Top.CfgValue])
    assert root.Top.CfgValue.hidden is False


def test_node_reduce_add_iterable_and_array_helpers():
    root = NodeEdgeRoot()

    # add() accepts iterables of Nodes and registers array-style children in both
    # the flat node list and the array lookup structure.
    root.Top.add([
        pr.LocalVariable(name="ExtraArray[0]", value=1),
        pr.LocalVariable(name="ExtraArray[1]", value=2),
    ])
    assert root.Top.ExtraArray[0].value() == 1
    assert root.Top.ExtraArray[1].value() == 2

    reduced = ExposedNode(name="Expose").__reduce__()
    factory, args = reduced
    assert factory is pr_interfaces.VirtualFactory
    attrs = args[0]
    assert attrs["name"] == "Expose"
    assert "exposed_prop" in attrs["props"]
    assert attrs["funcs"]["exposed_method"]["args"] == ["arg"]
    assert attrs["funcs"]["exposed_method"]["kwargs"] == ["kw"]


def test_node_recursive_helpers_and_managed_interfaces():
    root = NodeEdgeRoot()
    root.start()
    try:
        assert root.managed.started == 1

        root.Top.callRecursive("mark", nodeTypes=[RecursiveDevice], token="seen")
        assert root.Top.marker == ["seen"]
        assert root.Top.Child.marker == ["seen"]
        assert root.Top.Array[0].marker == ["seen"]
        assert root.Top.Array[1].marker == ["seen"]

        marker = root.Top.makeRecursive("mark", nodeTypes=[RecursiveDevice])
        marker(token="again")
        assert root.Top.Child.marker == ["seen", "again"]
    finally:
        root.stop()

    assert root.managed.stopped == 1


def test_node_set_dict_with_array_matches_and_invalid_keys(caplog):
    with NodeEdgeRoot() as root:
        # Array slices fan out to every matched node in the subtree.
        root.Top._setDict(
            d={"Array[:]": {"CfgValue": 9}},
            writeEach=False,
            modes=["RW"],
            incGroups=None,
            excGroups=None,
        )
        assert root.Top.Array[0].CfgValue.value() == 9
        assert root.Top.Array[1].CfgValue.value() == 9

        # Keys on a non-array node should log an error and not raise.
        root.Top._setDict(
            d={"Child[1]": {"CfgValue": 7}},
            writeEach=False,
            modes=["RW"],
            incGroups=None,
            excGroups=None,
        )
        assert "Entry Child with key ['1'] not found" in caplog.text


def test_device_set_poll_interval_and_repeated_remote_variables():
    with NodeEdgeRoot() as root:
        root.Top.CfgValue.setPollInterval(1.0)
        root.Top.setPollInterval(5.0)
        assert root.Top.CfgValue.pollInterval == 5.0

        root.Top.setPollInterval(7.5, variables=["CfgValue"])
        assert root.Top.CfgValue.pollInterval == 7.5

    with RepeatedRoot() as root:
        repeated = root.Pack.RepeatedField
        assert sorted(repeated.keys()) == [0, 1, 2]

        repeated[0].set(4, write=False)
        repeated[1].set(5, write=False)
        repeated[2].set(6, write=False)
        assert repeated[0].value() == 4
        assert repeated[1].value() == 5
        assert repeated[2].value() == 6


def test_node_add_errors_and_special_name_warning(monkeypatch):
    root = NodeEdgeRoot()
    try:
        with pytest.raises(pr.NodeError, match="non device node"):
            root.Top.CfgValue.add(pr.LocalVariable(name="Nested", value=1))

        attached = pr.LocalVariable(name="Attached", value=3)
        # Simulate a node that is already attached elsewhere without needing to
        # start a second tree just to populate ``_parent``.
        attached._parent = root.Top
        with pytest.raises(pr.NodeError, match="already attached"):
            root.Top.Child.add(attached)

        root.start()
        with pytest.raises(pr.NodeError, match="already started"):
            root.Top.Child.add(root.Top.CfgValue)
    finally:
        if root.running:
            root.stop()

    root = NodeEdgeRoot()
    warnings = []
    monkeypatch.setattr(root.Top._log, "warning", lambda *args: warnings.append(args))
    root.Top.add(pr.LocalVariable(name="Bad-Name", value=1))
    assert warnings == [("Node %s with one or more special characters will cause lookup errors.", "Bad-Name")]


def test_iterate_dict_slice_holes_and_array_device_generation(tmp_path, capsys):
    root = NodeEdgeRoot()

    # Sparse array keys should still allow slice lookup without raising.
    root.Top.add(pr.LocalVariable(name="Sparse[3]", value=7))
    nodes, keys = root.Top.nodeMatch("Sparse[1:4]")
    assert [node.path for node in nodes] == ["Sparse[3]"]
    assert keys is None

    class ArrayRoot(pr.Root):
        def __init__(self):
            super().__init__(name="root", pollEn=False)
            self.add(pr.ArrayDevice(
                name="LeafArray",
                arrayClass=ArrayLeaf,
                number=2,
                stride=0x10,
                arrayArgs=[{"name": "Custom[0]"}, {}],
            ))

    with ArrayRoot() as array_root:
        assert array_root.LeafArray.Custom[0].LeafValue.value() == 0
        assert array_root.LeafArray.ArrayLeaf[1].LeafValue.value() == 0x10

        # printYaml() is a thin wrapper, but capturing its output closes a
        # branch in Node and verifies it delegates to getYaml() correctly.
        array_root.LeafArray.printYaml(readFirst=False, recurse=True)
        out = capsys.readouterr().out
        assert "LeafValue: 0" in out

        array_root.LeafArray.genDocuments(str(tmp_path))
        top_doc = (tmp_path / "root_LeafArray.rst").read_text()
        child_doc = (tmp_path / "root_LeafArray_Custom[0].rst").read_text()
        assert "Sub Devices:" in top_doc
        assert "Variable List" in child_doc
