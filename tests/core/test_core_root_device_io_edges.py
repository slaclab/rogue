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
import threading
from pathlib import Path

import pyrogue as pr
import pytest
from conftest import MemoryRoot


class ManagedThing:
    def __init__(self, name):
        self.name = name
        self.started = 0
        self.stopped = 0

    def _start(self):
        self.started += 1

    def _stop(self):
        self.stopped += 1


class IoChild(pr.Device):
    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, **kwargs)
        self.add(pr.RemoteVariable(
            name="RemoteValue",
            offset=0x10,
            bitSize=8,
            base=pr.UInt,
            mode="RW",
        ))
        self.add(pr.LocalVariable(name="LocalCfg", value=2, groups=["Cfg"]))


class IoRoot(MemoryRoot):
    def __init__(self):
        super().__init__(name="root")
        self.primary = ManagedThing("primary")
        self.proto = ManagedThing("proto")
        self.extra = ManagedThing("extra")

        self.add(pr.Device(name="Top", memBase=self._mem))
        self.Top.add(pr.RemoteVariable(
            name="RemoteValue",
            offset=0x0,
            bitSize=8,
            base=pr.UInt,
            mode="RW",
            groups=["Cfg"],
            description="Remote config value",
        ))
        self.Top.add(pr.LocalVariable(
            name="PolledCfg",
            value=1,
            pollInterval=1.0,
            groups=["Cfg"],
            description="Polled local config",
        ))
        self.Top.add(IoChild(name="Child", offset=0x20, mem_base=self._mem))

        # Exercise all three managed-interface registration helpers.
        self.Top.addInterface([self.primary])
        self.Top.addProtocol(self.proto)
        self.Top.manage(self.extra)


def test_root_poll_block_restores_counter_on_exception():
    with IoRoot() as root:
        assert root._pollQueue.blockCount == 0

        with pytest.raises(RuntimeError, match="boom"):
            with root.pollBlock():
                assert root._pollQueue.blockCount == 1
                raise RuntimeError("boom")

        assert root._pollQueue.blockCount == 0


def test_root_operation_lock_is_reentrant_and_blocks_other_threads():
    root = pr.Root(name="root", pollEn=False)
    acquired = threading.Event()

    def worker():
        with root.operationLock():
            acquired.set()

    with root.operationLock():
        with root.operationLock():
            pass

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(timeout=0.1)
        assert thread.is_alive()
        assert not acquired.is_set()

    assert acquired.wait(timeout=1.0)
    thread.join(timeout=1.0)
    assert not thread.is_alive()


def test_yaml_operations_require_root(tmp_path):
    config = tmp_path / "detached.yml"
    config.write_text("Detached:\n  LocalCfg: 3\n")

    node = pr.Device(name="Detached")
    node.add(pr.LocalVariable(name="LocalCfg", value=1, mode="RW"))

    with pytest.raises(pr.NodeError, match="Detached is not attached to a Root"):
        node.getYaml(readFirst=False, modes=["RW"])

    with pytest.raises(pr.NodeError, match="Detached is not attached to a Root"):
        node.saveYaml(name=str(tmp_path / "detached_out.yml"), readFirst=False, modes=["RW"])

    with pytest.raises(pr.NodeError, match="Detached is not attached to a Root"):
        node.loadYaml(name=str(config), writeEach=False, modes=["RW"])

    with pytest.raises(pr.NodeError, match="Detached is not attached to a Root"):
        node.setYaml(yml="Detached:\n  LocalCfg: 4\n", writeEach=False, modes=["RW"])


def test_root_load_yaml_waits_for_operation_lock(tmp_path):
    config = tmp_path / "locked_load.yml"
    config.write_text("root.Top:\n  RemoteValue: 17\n")

    with IoRoot() as root:
        done = threading.Event()
        errors = []

        def load_config():
            try:
                root.loadYaml(name=str(config), writeEach=False, modes=["RW"])
            except Exception as exc:
                errors.append(exc)
            finally:
                done.set()

        with root.operationLock():
            thread = threading.Thread(target=load_config)
            thread.start()
            assert not done.wait(timeout=0.1)

        assert done.wait(timeout=5.0)
        thread.join(timeout=1.0)
        assert not thread.is_alive()
        assert errors == []
        assert root.Top.RemoteValue.value() == 17


def test_device_yaml_import_waits_for_operation_lock(tmp_path):
    config = tmp_path / "locked_subtree_load.yml"
    config.write_text("Top:\n  RemoteValue: 23\n")

    with IoRoot() as root:
        load_done = threading.Event()
        set_done = threading.Event()
        errors = []

        def load_subtree_yaml():
            try:
                root.Top.loadYaml(name=str(config), writeEach=False, modes=["RW"])
            except Exception as exc:
                errors.append(exc)
            finally:
                load_done.set()

        def set_subtree_yaml():
            try:
                root.Top.setYaml(yml="Top:\n  PolledCfg: 11\n", writeEach=False, modes=["RW"])
            except Exception as exc:
                errors.append(exc)
            finally:
                set_done.set()

        with root.operationLock():
            load_thread = threading.Thread(target=load_subtree_yaml)
            set_thread = threading.Thread(target=set_subtree_yaml)
            load_thread.start()
            set_thread.start()
            assert not load_done.wait(timeout=0.1)
            assert not set_done.wait(timeout=0.1)

        assert load_done.wait(timeout=5.0)
        assert set_done.wait(timeout=5.0)
        load_thread.join(timeout=1.0)
        set_thread.join(timeout=1.0)

        assert not load_thread.is_alive()
        assert not set_thread.is_alive()
        assert errors == []
        assert root.Top.RemoteValue.value() == 23
        assert root.Top.PolledCfg.value() == 11


def test_device_yaml_export_waits_for_operation_lock(tmp_path):
    out = tmp_path / "subtree.yml"

    with IoRoot() as root:
        yaml_done = threading.Event()
        save_done = threading.Event()
        yaml_results = []

        def get_subtree_yaml():
            yaml_results.append(root.Top.getYaml(readFirst=False, modes=["RW"]))
            yaml_done.set()

        def save_subtree_yaml():
            root.Top.saveYaml(name=str(out), readFirst=False, modes=["RW"])
            save_done.set()

        with root.operationLock():
            yaml_thread = threading.Thread(target=get_subtree_yaml)
            save_thread = threading.Thread(target=save_subtree_yaml)
            yaml_thread.start()
            save_thread.start()
            assert not yaml_done.wait(timeout=0.1)
            assert not save_done.wait(timeout=0.1)

        assert yaml_done.wait(timeout=5.0)
        assert save_done.wait(timeout=5.0)
        yaml_thread.join(timeout=1.0)
        save_thread.join(timeout=1.0)

        assert not yaml_thread.is_alive()
        assert not save_thread.is_alive()
        assert "Top:" in yaml_results[0]
        assert out.exists()


def test_root_wait_on_update_and_clear_log(wait_until):
    with IoRoot() as root:
        with root.updateGroup():
            root.Top.PolledCfg.set(5)
            root.Top.Child.LocalCfg.set(7)

        root.waitOnUpdate()
        assert root.Top.PolledCfg.value() == 5
        assert root.Top.Child.LocalCfg.value() == 7

        root.SystemLog.set('[{"message": "x"}]')
        root.SystemLogLast.set("last")
        root._clearLog()
        assert root.SystemLog.value() == "[]"
        assert root.SystemLogLast.value() == ""


def test_device_interface_management_and_custom_block_sorting():
    root = IoRoot()
    root.Top.addCustomBlock(type("Block", (), {"offset": 8, "size": 4})())
    root.Top.addCustomBlock(type("Block", (), {"offset": 4, "size": 8})())
    assert [(block.offset, block.size) for block in root.Top._custBlocks] == [(4, 8), (8, 4)]

    root.start()
    try:
        assert root.primary.started == 1
        assert root.proto.started == 1
        assert root.extra.started == 1
    finally:
        root.stop()

    assert root.primary.stopped == 1
    assert root.proto.stopped == 1
    assert root.extra.stopped == 1


def test_root_save_yaml_zip_and_load_yaml_from_zip_dir(tmp_path):
    with IoRoot() as root:
        zip_path = tmp_path / "config.zip"
        root.Top.RemoteValue.set(9)
        root.Top.Child.LocalCfg.set(11)

        root.saveYaml(
            name=str(zip_path),
            readFirst=False,
            modes=["RW"],
            incGroups=None,
            autoCompress=True,
        )

        with zipfile.ZipFile(zip_path, "r", compression=zipfile.ZIP_LZMA) as zf:
            names = zf.namelist()
            assert len(names) == 1
            saved_yaml = zf.read(names[0]).decode("utf-8")
            assert "RemoteValue: 0x9" in saved_yaml

        load_zip = tmp_path / "load.zip"
        with zipfile.ZipFile(load_zip, "w", compression=zipfile.ZIP_LZMA) as zf:
            zf.writestr("cfg/one.yml", "root.Top:\n  RemoteValue: 14\n")
            zf.writestr("cfg/two.yaml", "root.Top.Child:\n  LocalCfg: 21\n")
            zf.writestr("cfg/nested/skip.yml", "root.Top:\n  RemoteValue: 99\n")

        root.loadYaml(
            name=f"{load_zip}/cfg",
            writeEach=False,
            modes=["RW"],
            incGroups="Cfg",
        )

        assert root.Top.RemoteValue.value() == 14
        assert root.Top.Child.LocalCfg.value() == 21


def test_root_load_config_and_save_config_round_trip(tmp_path):
    config_in = Path(__file__).with_name("fixtures") / "load_config_input.yml"
    config_out = tmp_path / "output.yml"

    with IoRoot() as root:
        # Keep one smoke test for the command-style config wrappers so the
        # newer YAML tests do not need to duplicate the older API surface.
        root.LoadConfig(str(config_in))
        root.SaveConfig(str(config_out))

        assert root.Top.RemoteValue.value() == 5
        assert root.Top.Child.LocalCfg.value() == 7

    saved = pr.yamlToData(fName=str(config_out))
    assert saved["root"]["Top"]["RemoteValue"] == 0x5
    assert saved["root"]["Top"]["Child"]["LocalCfg"] == 7


def test_root_remote_variable_dump_and_invalid_load_path(tmp_path, monkeypatch):
    with IoRoot() as root:
        dumps = []

        # The dump helper only checks for the presence of _getDumpValue, so a
        # small bound method is enough to exercise the file path.
        monkeypatch.setattr(
            root.Top.RemoteValue,
            "_getDumpValue",
            lambda read_first: dumps.append(read_first) or "root.Top.RemoteValue = 3\n",
        )
        monkeypatch.setattr(root, "_read", lambda: dumps.append("read") or True)

        out = tmp_path / "dump.txt"
        assert root.remoteVariableDump(str(out), modes=["RW"], readFirst=True) is True
        assert dumps == ["read", False]
        dump_text = out.read_text()
        assert "root.Top.RemoteValue = 3\n" in dump_text
        assert "root.Top.Child.RemoteValue = 0\n" in dump_text

        with pytest.raises(Exception, match="must be a directory or end in .yml or .yaml"):
            root.loadYaml(name=str(tmp_path / "bad.txt"), writeEach=False, modes=["RW"])


def test_device_hide_variables_string_list_branch():
    root = IoRoot()
    root.Top.hideVariables(True, variables=["PolledCfg"])
    assert root.Top.PolledCfg.hidden is True
    root.Top.hideVariables(False, variables=["PolledCfg"])
    assert root.Top.PolledCfg.hidden is False
