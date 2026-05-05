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

# Locate the repository root relative to this file:
#   tests/utilities/<this file>  -> 3 levels up -> repo root
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _read_src(relative_path):
    """Read a source file relative to the repository root."""
    return (_REPO_ROOT / relative_path).read_text()


def test_streamzip_uses_64bit_total_out():
    # StreamZip::acceptFrame originally read strm.total_out_lo32 (lower 32 bits
    # of the bzip2 64-bit output counter) in isolation.  Compressed output
    # exceeding 4 GiB was silently truncated.  Two valid fixes:
    #   (a) Drop total_out_lo32 entirely (manual uint64_t accumulator, or the
    #       bzip2 64-bit extension API).  Token absent.
    #   (b) Combine total_out_hi32 << 32 | total_out_lo32 into a 64-bit value.
    #       Both tokens present.
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
    # StreamUnZip::acceptFrame originally read strm.total_out_lo32 only after
    # BZ2_bzDecompressEnd().  Same truncation risk for decompressed data
    # exceeding 4 GiB.  Same pair of valid fixes as the StreamZip path above.
    src = _read_src("src/rogue/utilities/StreamUnZip.cpp")
    has_lo32 = "total_out_lo32" in src
    has_hi32 = "total_out_hi32" in src
    assert (not has_lo32) or has_hi32, (
        "StreamUnZip uses 32-bit total_out_lo32 in isolation; truncates "
        "decompressed output larger than 4 GiB.  Either drop total_out_lo32 "
        "or pair it with total_out_hi32 for a 64-bit total_out value."
    )


def test_streamzip_handles_bz_param_error():
    # StreamZip::acceptFrame originally checked BZ2_bzCompress return only for
    # BZ_SEQUENCE_ERROR; BZ_PARAM_ERROR and other negative codes silently fell
    # through, so a misaligned-buffer error left the bzip2 stream initialized
    # without BZ2_bzCompressEnd -> bzip2 state leak.  Two valid fixes:
    #   (a) Name BZ_PARAM_ERROR explicitly in the state machine.
    #   (b) Generic negative-code check (e.g. `ret < 0`).  All bzip2 errors
    #       are negative; this is the canonical generic guard.
    src = _read_src("src/rogue/utilities/StreamZip.cpp")
    handles_more_codes = ("BZ_PARAM_ERROR" in src) or ("ret < 0" in src)
    assert handles_more_codes, (
        "StreamZip does not catch BZ2_bzCompress error codes beyond "
        "BZ_SEQUENCE_ERROR; can leak bzip2 state on misaligned buffers.  "
        "Either name BZ_PARAM_ERROR explicitly or use a generic negative-"
        "return-code check (ret < 0) together with cleanup."
    )
