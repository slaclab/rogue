from collections import OrderedDict as odict

import pyrogue as pr
import pyrogue._HelperFunctions as hf
import pytest


def test_unified_logging_toggle(monkeypatch):
    state = {"forward": False, "stdout": True}

    monkeypatch.setattr(hf.rogue.Logging, "setForwardPython", lambda value: state.__setitem__("forward", value))
    monkeypatch.setattr(hf.rogue.Logging, "setEmitStdout", lambda value: state.__setitem__("stdout", value))
    monkeypatch.setattr(hf.rogue.Logging, "forwardPython", lambda: state["forward"])
    monkeypatch.setattr(hf.rogue.Logging, "emitStdout", lambda: state["stdout"])

    pr.setUnifiedLogging(True)
    assert pr.unifiedLoggingEnabled() is True

    pr.setUnifiedLogging(False)
    assert pr.unifiedLoggingEnabled() is False


def test_add_library_path_handles_relative_absolute_and_zip(tmp_path, monkeypatch):
    rel_dir = tmp_path / "relative-lib"
    rel_dir.mkdir()
    abs_dir = tmp_path / "absolute-lib"
    abs_dir.mkdir()
    zip_path = tmp_path / "bundle.zip"
    zip_path.write_bytes(b"placeholder")

    monkeypatch.setattr(hf.sys, "argv", [str(tmp_path / "runner.py")])
    monkeypatch.setattr(hf.sys, "path", [])

    pr.addLibraryPath("relative-lib")
    pr.addLibraryPath(str(abs_dir))
    # Zip paths are validated against the archive itself, not the nested entry.
    pr.addLibraryPath(f"{zip_path}/pkg")

    assert hf.sys.path[0] == f"{zip_path}/pkg"
    assert hf.sys.path[1] == str(abs_dir)
    assert hf.sys.path[2] == str(rel_dir)

    with pytest.raises(Exception, match="does not exist"):
        pr.addLibraryPath("missing-lib")


def test_yaml_helpers_support_includes_zip_and_ordered_updates(tmp_path):
    child = tmp_path / "child.yaml"
    child.write_text("leaf: 7\n")

    parent = tmp_path / "parent.yaml"
    parent.write_text("top:\n  nested: !include child.yaml\n")

    archive = tmp_path / "config.zip"
    import zipfile
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_LZMA) as zf:
        zf.writestr("inside/config.yaml", "zipLeaf: 11\n")

    parsed = pr.yamlToData(fName=str(parent))
    zipped = pr.yamlToData(fName=f"{archive}/inside/config.yaml")

    assert isinstance(parsed, odict)
    assert parsed["top"]["nested"]["leaf"] == 7
    assert zipped["zipLeaf"] == 11

    data = {"root": {"existing": 1}}
    pr.keyValueUpdate(data, "root.branch.leaf", 9)
    pr.dictUpdate(data, {"root.extra": 5, "root": {"merged": 6}})
    pr.yamlUpdate(data, "root.yamlLeaf: 12\nother.value: 13\n")

    assert data == {
        "root": {
            "existing": 1,
            "branch": {"leaf": 9},
            "merged": 6,
            "extra": 5,
            "yamlLeaf": 12,
        },
        "other": {"value": 13},
    }

    restored = pr.recreate_OrderedDict("ignored", {"items": [("a", 1), ("b", 2)]})
    assert restored == odict([("a", 1), ("b", 2)])


def test_data_to_yaml_formats_variable_values_and_preserves_order():
    var = pr.LocalVariable(name="Value", value=5, disp="0x{:x}")
    enum_var = pr.LocalVariable(name="EnumValue", value=1, enum={1: "One"})
    bool_var = pr.LocalVariable(name="BoolValue", value=True)

    payload = odict([
        ("value", var.getVariableValue(read=False)),
        ("enum", enum_var.getVariableValue(read=False)),
        ("flag", bool_var.getVariableValue(read=False)),
    ])

    text = pr.dataToYaml(payload)

    # OrderedDict output should preserve the insertion order callers rely on.
    assert text.index("value:") < text.index("enum:") < text.index("flag:")
    assert "value: 0x5" in text
    assert "enum: One" in text
    assert pr.yamlToData(text)["flag"] is True


def test_function_wrapper_filters_supported_arguments():
    def full(root=None, dev=None, arg=None):
        return root, dev, arg

    wrapped = pr.functionWrapper(full, ["root", "dev", "cmd", "arg"])
    assert wrapped(full, "r", "d", "ignored", 3) == ("r", "d", 3)

    def no_args():
        return "done"

    wrapped_no_args = pr.functionWrapper(no_args, ["root", "dev"])
    assert wrapped_no_args(no_args, "r", "d") == "done"

    class CallableWithoutSignature:
        def __call__(self, *args, **kwargs):
            raise AssertionError("wrapper should not forward args for opaque callables")

    opaque = CallableWithoutSignature()

    original_getfullargspec = hf.inspect.getfullargspec

    def fake_getfullargspec(function):
        if function is opaque:
            raise TypeError("opaque")
        return original_getfullargspec(function)

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(hf.inspect, "getfullargspec", fake_getfullargspec)
    try:
        wrapped_opaque = pr.functionWrapper(opaque, ["root", "dev"])
        with pytest.raises(AssertionError, match="opaque callables"):
            wrapped_opaque(opaque, "r", "d")
    finally:
        monkeypatch.undo()

    assert pr.functionWrapper(None, ["root", "dev"])(None, "r", "d") is None


def test_doc_helpers_render_expected_rst_fragments():
    header = pr.genDocTableHeader(["Name", "Value"], indent=2, width=8)
    row = pr.genDocTableRow(["Field", "7"], indent=2, width=8)
    desc = pr.genDocDesc("First sentence. Second sentence", indent=4)

    assert header == "  +--------+--------+\n  |Name    |Value   |\n  +========+========+"
    assert row == "  |Field   |7       |\n  +--------+--------+"
    assert desc == "    | First sentence.\n    | Second sentence.\n"
