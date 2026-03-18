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


class ChildDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add(pr.LocalVariable(name="CfgValue", value=1, groups=["Cfg"]))
        self.add(pr.LocalVariable(name="StatusValue", value=2, mode="RO", groups=["Status"]))


class RecordingInterface:
    def __init__(self):
        self.started = 0
        self.stopped = 0

    def _start(self):
        self.started += 1

    def _stop(self):
        self.stopped += 1


class TreeRoot(pr.Root):
    def __init__(self):
        super().__init__(name="root", pollEn=False)
        self.recording = RecordingInterface()
        self.addInterface(self.recording)
        self.add(ChildDevice(name="Child"))
        self.add(ChildDevice(name="ArrayChild[0]"))
        self.add(ChildDevice(name="ArrayChild[1]"))


def test_root_get_node_and_array_lookup():
    with TreeRoot() as root:
        assert root.getNode("root") is root
        assert root.getNode("root.Child") is root.Child
        assert root.getNode("root.ArrayChild[1]") is root.ArrayChild[1]
        assert root.ArrayChild[0].path == "root.ArrayChild[0]"
        assert root.getNode("missing.path") is None


def test_duplicate_add_rejected_before_start():
    root = TreeRoot()
    with pytest.raises(pr.NodeError, match="Name collision"):
        root.add(ChildDevice(name="Child"))


def test_tree_dict_yaml_and_var_listener_filters(wait_until, tmp_path):
    updates = []

    with TreeRoot() as root:
        root.addVarListener(lambda path, value: updates.append((path, value.value)), incGroups="Cfg")

        with root.updateGroup():
            # Queue two updates together so the listener filter is tested against
            # a realistic batched Root update cycle.
            root.Child.CfgValue.set(9)
            root.Child.StatusValue.set(10)

        assert wait_until(lambda: any(path == "root.Child.CfgValue" for path, _ in updates))
        assert all(path != "root.Child.StatusValue" for path, _ in updates)

        tree = root.Child._getDict(modes=["RW"], incGroups="Cfg", excGroups=None)
        assert "CfgValue" in tree
        assert "StatusValue" not in tree

        yaml_text = root.getYaml(readFirst=False, modes=["RW"], incGroups="Cfg", recurse=True)
        assert yaml_text == "root: null\n"

        out_file = tmp_path / "cfg.yml"
        root.saveYaml(name=str(out_file), readFirst=False, modes=["RW"], incGroups="Cfg", excGroups=None)
        assert out_file.exists()


def test_root_start_stop_manages_interfaces():
    root = TreeRoot()
    assert root.running is False
    root.start()
    try:
        assert root.running is True
        assert root.recording.started == 1
    finally:
        root.stop()

    assert root.running is False
    assert root.recording.stopped == 1
