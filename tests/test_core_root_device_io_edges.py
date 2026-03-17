import zipfile

import pyrogue as pr
import pytest
import rogue.interfaces.memory


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


class IoRoot(pr.Root):
    def __init__(self):
        super().__init__(name="root", pollEn=False)
        self._mem = rogue.interfaces.memory.Emulate(4, 0x4000)
        self.addInterface(self._mem)

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
