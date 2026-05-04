#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Regression tests.
#   Each test calls a yamlToData entry-point with a malicious YAML payload
#   that uses !!python/object/apply to invoke os.getenv.  Because
#   PyrogueLoader extends yaml.Loader (a full Loader), the tag executes on
#   HEAD, reads a known sentinel env-var, and the test FAILS with the
#   expected assertion message.
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

import pyrogue._HelperFunctions as hf


# ---------------------------------------------------------------------------
# string-input path (yamlToData(stream=...), line 261)
# ---------------------------------------------------------------------------
def test_yaml_loader_string_path_unsafe(monkeypatch):
    """PyrogueLoader allows !!python/object/apply on string input."""
    monkeypatch.setenv("AUDIT_PYR_001_SENTINEL", "compromised_001")

    malicious = "!!python/object/apply:os.getenv ['AUDIT_PYR_001_SENTINEL']"
    result = hf.yamlToData(stream=malicious)

    assert result != "compromised_001", (
        "PyrogueLoader allowed arbitrary !!python/object/apply "
        "construction; sentinel value compromised (string-input path, line 261)"
    )


# ---------------------------------------------------------------------------
# zip-archive branch (yamlToData(fName='...zip/sub'), line 272)
# ---------------------------------------------------------------------------
def test_yaml_loader_zip_branch_unsafe(monkeypatch, tmp_path):
    """PyrogueLoader allows !!python/object/apply on zip-archive branch."""
    monkeypatch.setenv("AUDIT_PYR_002_SENTINEL", "compromised_002")

    malicious = "!!python/object/apply:os.getenv ['AUDIT_PYR_002_SENTINEL']"
    zip_path = tmp_path / "payload.zip"
    inner = "config.yaml"

    with zipfile.ZipFile(str(zip_path), "w", compression=zipfile.ZIP_LZMA) as zf:
        zf.writestr(inner, malicious)

    fname = str(zip_path) + "/" + inner
    result = hf.yamlToData(fName=fname)

    assert result != "compromised_002", (
        "PyrogueLoader allowed arbitrary !!python/object/apply "
        "construction; sentinel value compromised (zip-archive branch, line 272)"
    )


# ---------------------------------------------------------------------------
# plain-file branch (yamlToData(fName='...yaml'), line 278)
# ---------------------------------------------------------------------------
def test_yaml_loader_file_branch_unsafe(monkeypatch, tmp_path):
    """PyrogueLoader allows !!python/object/apply on plain-file branch."""
    monkeypatch.setenv("AUDIT_PYR_003_SENTINEL", "compromised_003")

    malicious = "!!python/object/apply:os.getenv ['AUDIT_PYR_003_SENTINEL']"
    yaml_file = tmp_path / "payload.yaml"
    yaml_file.write_text(malicious)

    result = hf.yamlToData(fName=str(yaml_file))

    assert result != "compromised_003", (
        "PyrogueLoader allowed arbitrary !!python/object/apply "
        "construction; sentinel value compromised (plain-file branch, line 278)"
    )
