#!/usr/bin/env python3
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

import pyrogue.utilities.hls._RegInterfParser as parser


SAMPLE_HEADER = """\
#ifndef __APPLICATION_HW_H__
#define __APPLICATION_HW_H__

#define CTRL_REG_ADDR 0x100
#define CTRL_REG_BITS 32

#define STATUS_REG_ADDR 0x200
#define STATUS_REG_BITS 16

#define DATA_BUF_ADDR 0x300
#define DATA_BUF_WIDTH 32
#define DATA_BUF_DEPTH 64

#endif
"""


@pytest.fixture
def hls_zip(tmp_path):
    """Create a temporary zip file containing a mock HLS header."""
    hdr_dir = tmp_path / "solution" / "impl" / "ip"
    hdr_dir.mkdir(parents=True)
    hdr_file = hdr_dir / "test_hw.h"
    hdr_file.write_text(SAMPLE_HEADER)

    zip_path = tmp_path / "test_hls.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(hdr_file, arcname="solution/impl/ip/test_hw.h")

    return str(zip_path)


def test_parse_remote_variable(hls_zip, monkeypatch, tmp_path):
    monkeypatch.setattr('builtins.input', lambda _: hls_zip)
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(parser, 'vartype', 'RemoteVariable')
    result = parser.parse()

    assert len(result) > 0
    names = [r.name for r in result]
    assert any('CTRL' in n or 'STATUS' in n for n in names)

    for r in result:
        assert hasattr(r, 'name')
        assert hasattr(r, 'offset')
        assert hasattr(r, 'bitSize')


def test_parse_memory_device(hls_zip, monkeypatch, tmp_path):
    monkeypatch.setattr('builtins.input', lambda _: hls_zip)
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(parser, 'vartype', 'MemoryDevice')
    result = parser.parse()

    assert len(result) > 0
    for r in result:
        assert hasattr(r, 'name')
        assert hasattr(r, 'offset')
        assert hasattr(r, 'size')
        assert hasattr(r, 'wordBitSize')


def test_parse_remote_command(hls_zip, monkeypatch, tmp_path):
    monkeypatch.setattr('builtins.input', lambda _: hls_zip)
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(parser, 'vartype', 'RemoteCommand')
    result = parser.parse()

    assert len(result) > 0
    for r in result:
        assert hasattr(r, 'name')
        assert hasattr(r, 'offset')
        assert hasattr(r, 'bitSize')
        assert hasattr(r, 'function')


def test_parse_width_over_64_exits(monkeypatch, tmp_path):
    wide_header = """\
#define WIDE_REG_ADDR 0x400
#define WIDE_REG_BITS 128
"""
    hdr_dir = tmp_path / "solution"
    hdr_dir.mkdir()
    hdr_file = hdr_dir / "wide_hw.h"
    hdr_file.write_text(wide_header)

    zip_path = tmp_path / "wide_hls.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(hdr_file, arcname="solution/wide_hw.h")

    monkeypatch.setattr('builtins.input', lambda _: str(zip_path))
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(parser, 'vartype', 'RemoteVariable')
    with pytest.raises(SystemExit):
        parser.parse()


def test_parse_nonexistent_zip(monkeypatch, tmp_path):
    monkeypatch.setattr('builtins.input', lambda _: str(tmp_path / "missing.zip"))
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(parser, 'vartype', 'RemoteVariable')
    with pytest.raises(SystemExit):
        parser.parse()


def test_named_tuple_defaults():
    rv = parser.RemoteVariable()
    assert rv.name == 'VarName'
    assert rv.bitSize == 8
    assert rv.mode == 'RW'

    rc = parser.RemoteCommand()
    assert rc.name == 'CmdName'
    assert rc.bitSize == 8

    md = parser.MemoryDevice()
    assert md.name == 'DevName'
    assert md.wordBitSize == 8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
