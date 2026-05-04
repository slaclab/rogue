#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : StreamZip / StreamUnZip bzip2 audit repros
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
#   UTIL-007 -- StreamZip::acceptFrame uses 32-bit total_out_lo32; truncates
#               compressed output larger than 4 GiB
#   UTIL-008 -- StreamUnZip::acceptFrame reads total_out_lo32 only; same
#               truncation risk as UTIL-007
#   UTIL-009 -- StreamZip state machine only handles BZ_SEQUENCE_ERROR;
#               BZ_PARAM_ERROR is not caught, leaking bzip2 state
#
# All three assertions read the relevant production .cpp files.  On HEAD,
# each structural invariant is absent -> assertion fails deterministically.

import pathlib

# Locate the repository root relative to this file:
#   tests/utilities/<this file>  -> 3 levels up -> repo root
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _read_src(relative_path):
    """Read a source file relative to the repository root."""
    return (_REPO_ROOT / relative_path).read_text()


def test_streamzip_uses_64bit_total_out_util_007():
    # UTIL-007: StreamZip::acceptFrame at
    # src/rogue/utilities/StreamZip.cpp line ~119 reads
    # strm.total_out_lo32 (lower 32 bits of the bzip2 64-bit output counter).
    # For compressed output exceeding 4 GiB the payload is silently truncated.
    # The fix combines total_out_hi32 and total_out_lo32 into a 64-bit value
    # or uses a 64-bit payload API.  On HEAD only total_out_lo32 is referenced.
    src = _read_src("src/rogue/utilities/StreamZip.cpp")
    assert "total_out_lo32" not in src, (
        "UTIL-007: StreamZip uses 32-bit total_out_lo32; truncates compressed "
        "output larger than 4 GiB; should combine total_out_hi32 and "
        "total_out_lo32 for 64-bit payload"
    )


def test_streamunzip_uses_64bit_total_out_util_008():
    # UTIL-008: StreamUnZip::acceptFrame at
    # src/rogue/utilities/StreamUnZip.cpp line ~128 reads strm.total_out_lo32
    # only after BZ2_bzDecompressEnd().  Same truncation risk as UTIL-007 for
    # decompressed data exceeding 4 GiB.
    src = _read_src("src/rogue/utilities/StreamUnZip.cpp")
    assert "total_out_lo32" not in src, (
        "UTIL-008: StreamUnZip uses 32-bit total_out_lo32; truncates "
        "decompressed output larger than 4 GiB; should use 64-bit total_out"
    )


def test_streamzip_handles_bz_param_error_util_009():
    # UTIL-009: StreamZip::acceptFrame at
    # src/rogue/utilities/StreamZip.cpp line ~91 checks BZ2_bzCompress return
    # only for BZ_SEQUENCE_ERROR.  BZ_PARAM_ERROR and other non-OK codes are
    # not handled; a misaligned buffer can trigger BZ_PARAM_ERROR which is
    # silently ignored, leaving the bzip2 stream initialized without
    # BZ2_bzCompressEnd being called -> bzip2 state leak.
    src = _read_src("src/rogue/utilities/StreamZip.cpp")
    assert "BZ_PARAM_ERROR" in src, (
        "UTIL-009: StreamZip does not handle BZ_PARAM_ERROR; can leak bzip2 "
        "state on misaligned buffers; state machine should validate all "
        "BZ2_bzCompress return codes"
    )
