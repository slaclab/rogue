import pyrogue as pr
import pyrogue.utilities.cpsw as cpsw
import rogue.interfaces.memory


class CpswChild(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(description="Child device", **kwargs)
        self.add(pr.RemoteVariable(
            name="ChildInt",
            description="Child integer",
            offset=0x0,
            bitSize=8,
            base=pr.Int,
            mode="RW",
        ))


class CpswDevice(pr.Device):
    def __init__(self, mem_base, **kwargs):
        super().__init__(memBase=mem_base, description="Parent device", **kwargs)

        self.add(pr.RemoteVariable(
            name="IntVar",
            description="Signed integer",
            offset=0x0,
            bitSize=8,
            base=pr.Int,
            mode="RW",
            enum={1: "One"},
        ))

        self.add(pr.RemoteVariable(
            name="BoolVar",
            description="Boolean value",
            offset=0x4,
            bitSize=1,
            base=pr.Bool,
            mode="RO",
            disp="0x{:x}",
        ))

        self.add(pr.RemoteVariable(
            name="StringVar",
            description="ASCII text",
            offset=0x8,
            bitSize=32,
            base=pr.String,
            mode="RW",
        ))

        self.add(pr.LocalVariable(name="LocalVar", value=3, description="Local only"))
        self.add(pr.LinkVariable(name="LinkVar", variable=self.IntVar, description="Linked value"))
        self.add(pr.LocalCommand(name="DoThing", function=lambda: None, description="Command only"))
        self.add(CpswChild(name="Child", offset=0x20, memBase=mem_base))


class CpswRoot(pr.Root):
    def __init__(self):
        super().__init__(name="root", pollEn=False)
        mem = rogue.interfaces.memory.Emulate(4, 0x4000)
        self.addInterface(mem)
        self.add(CpswDevice(name="Dev", mem_base=mem))


def test_export_remote_variable_formats_supported_types():
    with CpswRoot() as root:
        text, size = cpsw.exportRemoteVariable(root.Dev.IntVar, indent=2)
        assert size == 1
        assert "IntVar:" in text
        assert "offset: 0x0" in text
        assert "sizeBits: 8" in text
        assert "mode: RW" in text
        assert "description: Signed integer" in text
        assert "- name: One" in text

        bool_text, bool_size = cpsw.exportRemoteVariable(root.Dev.BoolVar, indent=2)
        assert bool_size == 5
        assert "encoding: 16" in bool_text
        assert "lsBit: 0" in bool_text

        string_text, string_size = cpsw.exportRemoteVariable(root.Dev.StringVar, indent=2)
        assert string_size == 12
        assert "encoding: ASCII" in string_text
        assert "nelms: 4" in string_text


def test_placeholder_exporters_include_context():
    with CpswRoot() as root:
        local_text = cpsw.exportLocalVariable(root.Dev.LocalVar, indent=2)
        link_text = cpsw.exportLinkVariable(root.Dev.LinkVar, indent=2)
        cmd_text = cpsw.exportCommand(root.Dev.DoThing, indent=2)

        assert "#Unsupported Local Variable" in local_text
        assert "#LocalVar" in local_text
        assert "#Unsupported Link Variable" in link_text
        assert "#dependencies:" in link_text
        assert "#Unsupported Command" in cmd_text
        assert "#DoThing" in cmd_text


def test_export_device_and_root_write_yaml_files(tmp_path):
    with CpswRoot() as root:
        device_list = {}
        index, size = cpsw.exportDevice(root.Dev, device_list, str(tmp_path))
        assert index == 0
        assert size == 0x28

        dev_yaml = (tmp_path / "CpswDevice.yaml").read_text()
        child_yaml = (tmp_path / "CpswChild.yaml").read_text()

        # The generated file should keep the header/include prologue instead of
        # dropping directly into the MMIODev body.
        assert "#Auto Generated CPSW Yaml File" in dev_yaml
        assert "#once CpswDevice" in dev_yaml
        assert "#include CpswChild.yaml" in dev_yaml
        assert "CpswDevice: &CpswDevice" in dev_yaml
        assert "children:" in dev_yaml
        assert "Child:" in dev_yaml
        assert "<<: *CpswChild" in dev_yaml

        assert "#Auto Generated CPSW Yaml File" in child_yaml
        assert "CpswChild: &CpswChild" in child_yaml
        assert "ChildInt:" in child_yaml

        cpsw.exportRoot(root, str(tmp_path))
        assert (tmp_path / "CpswDevice.yaml").exists()
