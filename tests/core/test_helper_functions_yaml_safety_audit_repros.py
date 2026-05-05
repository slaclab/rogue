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

import pytest
import yaml

import pyrogue._HelperFunctions as hf


# ---------------------------------------------------------------------------
# string-input path (yamlToData(stream=...), line 261)
# ---------------------------------------------------------------------------
def test_yaml_loader_string_path_unsafe(monkeypatch):
    """PyrogueLoader must reject !!python/object/apply on string input.

    The unsafe tag must surface as a yaml.constructor.ConstructorError so
    callers (Root.loadYaml -> _setDictRoot, yamlUpdate -> dictUpdate) see
    the parse failure directly instead of receiving a None sentinel that
    crashes later in unrelated code with a confusing AttributeError.
    """
    monkeypatch.setenv("AUDIT_PYR_001_SENTINEL", "compromised_001")

    malicious = "!!python/object/apply:os.getenv ['AUDIT_PYR_001_SENTINEL']"
    with pytest.raises(yaml.constructor.ConstructorError):
        hf.yamlToData(stream=malicious)


# ---------------------------------------------------------------------------
# zip-archive branch (yamlToData(fName='...zip/sub'), line 272)
# ---------------------------------------------------------------------------
def test_yaml_loader_zip_branch_unsafe(monkeypatch, tmp_path):
    """PyrogueLoader must reject !!python/object/apply on the zip branch."""
    monkeypatch.setenv("AUDIT_PYR_002_SENTINEL", "compromised_002")

    malicious = "!!python/object/apply:os.getenv ['AUDIT_PYR_002_SENTINEL']"
    zip_path = tmp_path / "payload.zip"
    inner = "config.yaml"

    with zipfile.ZipFile(str(zip_path), "w", compression=zipfile.ZIP_LZMA) as zf:
        zf.writestr(inner, malicious)

    fname = str(zip_path) + "/" + inner
    with pytest.raises(yaml.constructor.ConstructorError):
        hf.yamlToData(fName=fname)


# ---------------------------------------------------------------------------
# plain-file branch (yamlToData(fName='...yaml'), line 278)
# ---------------------------------------------------------------------------
def test_yaml_loader_file_branch_unsafe(monkeypatch, tmp_path):
    """PyrogueLoader must reject !!python/object/apply on the plain-file branch."""
    monkeypatch.setenv("AUDIT_PYR_003_SENTINEL", "compromised_003")

    malicious = "!!python/object/apply:os.getenv ['AUDIT_PYR_003_SENTINEL']"
    yaml_file = tmp_path / "payload.yaml"
    yaml_file.write_text(malicious)

    with pytest.raises(yaml.constructor.ConstructorError):
        hf.yamlToData(fName=str(yaml_file))
