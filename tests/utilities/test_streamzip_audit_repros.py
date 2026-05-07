#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : StreamZip / StreamUnZip bzip2 regression test
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
#
# Deterministic source-text repros for:
#    -- StreamZip::acceptFrame uses 32-bit total_out_lo32; truncates
#               compressed output larger than 4 GiB
#    -- StreamUnZip::acceptFrame reads total_out_lo32 only; same
#               truncation risk
#    -- StreamZip state machine only handles BZ_SEQUENCE_ERROR;
#               BZ_PARAM_ERROR is not caught, leaking bzip2 state
#
# All three assertions read the relevant production.cpp files.  On HEAD,
# each structural invariant is absent -> assertion fails deterministically.

import pathlib
import re

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

_NEG_RET_RE = re.compile(r"\bret\s*<\s*0\b")


def _read_src(relative_path):
    """Read a source file relative to the repository root."""
    return (_REPO_ROOT / relative_path).read_text()


def test_streamzip_uses_64bit_total_out():
    src = _read_src("src/rogue/utilities/StreamZip.cpp")
    has_lo32 = "total_out_lo32" in src
    has_hi32 = "total_out_hi32" in src
    assert (not has_lo32) or has_hi32, (
        "StreamZip uses 32-bit total_out_lo32 in isolation; truncates "
        "compressed output larger than 4 GiB.  Either drop total_out_lo32 "
        "(manual 64-bit accumulator or bzip2 64-bit API) or pair it with "
        "total_out_hi32 to assemble a 64-bit total_out."
    )


def test_streamunzip_uses_64bit_total_out():
    src = _read_src("src/rogue/utilities/StreamUnZip.cpp")
    has_lo32 = "total_out_lo32" in src
    has_hi32 = "total_out_hi32" in src
    assert (not has_lo32) or has_hi32, (
        "StreamUnZip uses 32-bit total_out_lo32 in isolation; truncates "
        "decompressed output larger than 4 GiB.  Either drop total_out_lo32 "
        "or pair it with total_out_hi32 for a 64-bit total_out value."
    )


def test_streamzip_handles_bz_param_error():
    src = _read_src("src/rogue/utilities/StreamZip.cpp")
    handles_more_codes = ("BZ_PARAM_ERROR" in src) or bool(_NEG_RET_RE.search(src))
    assert handles_more_codes, (
        "StreamZip does not catch BZ2_bzCompress error codes beyond "
        "BZ_SEQUENCE_ERROR; can leak bzip2 state on misaligned buffers.  "
        "Either name BZ_PARAM_ERROR explicitly or use a generic negative-"
        "return-code check (ret < 0) together with cleanup."
    )
