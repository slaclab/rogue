#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : StreamReader / StreamWriter raw-resource regression test
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
#    -- StreamReader::open() uses raw ``new std::thread``
#    -- StreamWriter::setBufferSize() uses raw malloc instead of
#               std::vector
#    -- StreamReader::runThread reads frame size as uint32_t and
#               calls reqFrame without an upper-bound check
#
# All three assertions read the relevant production.cpp files and verify
# structural invariants that the fixed code must satisfy.  On HEAD, each
# invariant is absent -> assertion fails deterministically.

import pathlib

# Locate the repository root relative to this file:
#   tests/fileio/<this file>  -> 3 levels up -> repo root
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _read_src(relative_path):
    """Read a source file relative to the repository root."""
    return (_REPO_ROOT / relative_path).read_text()


def test_streamreader_uses_unique_ptr_thread():
    # StreamReader::open() at
    # src/rogue/utilities/fileio/StreamReader.cpp line ~95 allocates readThread_
    # with raw "new std::thread".  The codebase norm is std::unique_ptr<std::thread>.
    src = _read_src("src/rogue/utilities/fileio/StreamReader.cpp")
    assert "new std::thread" not in src, (
        "StreamReader::open uses raw new std::thread at line ~95; "
        "should be std::unique_ptr<std::thread>"
    )


def test_streamwriter_buffer_uses_vector():
    # StreamWriter::setBufferSize() at
    # src/rogue/utilities/fileio/StreamWriter.cpp line ~196 allocates buffer_
    # with raw malloc().  The idiomatic replacement is std::vector<uint8_t>.
    src = _read_src("src/rogue/utilities/fileio/StreamWriter.cpp")
    assert "malloc(" not in src, (
        "StreamWriter::setBufferSize uses raw malloc at line ~196; "
        "should use std::vector<uint8_t>"
    )


def test_streamreader_size_bound_check():
    # StreamReader::runThread at
    # src/rogue/utilities/fileio/StreamReader.cpp line ~186 reads frame size
    # as a raw uint32_t and calls reqFrame(size, true) without an upper-bound
    # check.  A corrupted file with size=0xFFFFFFFF would cause a huge allocation.
    # The fix adds a guard like: if (size > MAX_FRAME_SIZE) {... continue; }
    # On HEAD no such guard exists, so the assertion fails.
    src = _read_src("src/rogue/utilities/fileio/StreamReader.cpp")
    # Look for reqFrame call and verify an upper-bound guard precedes it
    lines = src.splitlines()
    req_frame_indices = [
        i for i, ln in enumerate(lines) if "reqFrame(size," in ln
    ]
    assert req_frame_indices, "reqFrame(size,...) call not found in StreamReader.cpp"

    for rf_idx in req_frame_indices:
        # Look at the 10 lines before reqFrame for an upper-bound check on size
        window = lines[max(0, rf_idx - 10):rf_idx]
        has_bound = any(
            ("size >" in ln or "size>=" in ln or "MAX_" in ln or "kMax" in ln
             or "UINT32_MAX" in ln or "maxSize" in ln)
            for ln in window
        )
        if not has_bound:
            raise AssertionError(
                "StreamReader reads size as uint32_t and calls "
                "reqFrame without upper-bound check on size; a corrupted file "
                "with size=0xFFFFFFFF will trigger a huge allocation"
            )
