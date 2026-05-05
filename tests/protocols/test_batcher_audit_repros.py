#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
# -----------------------------------------------------------------------------
# Description:
#   Regression tests
#   batcher V1/V2 InverterV1/InverterV2 acceptFrame() performs memcpy on
#   tail region without verifying that at least headerSize() bytes are
#   available before the copy.
# -----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# -----------------------------------------------------------------------------

import pathlib


_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_INV_V1 = _REPO_ROOT / "src" / "rogue" / "protocols" / "batcher" / "InverterV1.cpp"
_INV_V2 = _REPO_ROOT / "src" / "rogue" / "protocols" / "batcher" / "InverterV2.cpp"


def _read_source(path):
    return path.read_text()


def _has_tail_payload_guard(src, memcpy_tag):
    """Return True if a runtime payload-vs-tailsize bounds check precedes the memcpy."""
    lines = src.splitlines()
    memcpy_lineno = None
    for i, line in enumerate(lines):
        if memcpy_tag in line:
            memcpy_lineno = i
            break
    if memcpy_lineno is None:
        return False

    search_start = max(0, memcpy_lineno - 20)
    preceding = "\n".join(lines[search_start:memcpy_lineno])

    # Tokens indicating a runtime payload-size guard (excludes tailSize() metadata check)
    return any(
        token in preceding
        for token in (
            "getPayload()",
            "getSize()",
            "bytes_available",
            "frame->size",
            "payload_size",
            "frameSize",
            "frame_size",
            ">= headerSize() *",
            "* core.count()",
        )
    )


def _multiplication_is_64bit(src, memcpy_tag):
    """Return True if the bounds-check multiplication is performed in 64-bit."""
    lines = src.splitlines()
    memcpy_lineno = None
    for i, line in enumerate(lines):
        if memcpy_tag in line:
            memcpy_lineno = i
            break
    if memcpy_lineno is None:
        return False

    search_start = max(0, memcpy_lineno - 20)
    preceding = "\n".join(lines[search_start:memcpy_lineno])

    return ("uint64_t" in preceding) and ("headerSize()" in preceding)


def test_batcher_v1_memcpy_bounds_check():
    """Verify InverterV1::acceptFrame has a payload bounds check before memcpy."""
    src = _read_source(_INV_V1)

    assert "memcpy(core.beginHeader().ptr(), core.beginTail(0).ptr(), core.headerSize())" in src, \
        "expected memcpy pattern not found in InverterV1.cpp; file may have changed"

    has_guard = _has_tail_payload_guard(src, "memcpy(core.beginHeader")

    assert has_guard, (
        "V1 batcher memcpy lacks runtime frame-size bounds check — "
        "InverterV1::acceptFrame copies core.headerSize() bytes from tail region "
        "without verifying the frame payload holds at least headerSize()*count() "
        "bytes of tail data (the existing headerSize()!=tailSize() check only "
        "validates metadata consistency, not frame-buffer availability)"
    )

    assert _multiplication_is_64bit(src, "memcpy(core.beginHeader"), (
        "V1 batcher bounds-check multiplication is still in 32-bit arithmetic — "
        "headerSize() * (count() + 1) can wrap on a crafted oversized batcher "
        "frame and the comparison would then under-approximate the required "
        "tail bytes; promote one operand to uint64_t before the multiplication"
    )


def test_batcher_v2_memcpy_bounds_check():
    """Verify InverterV2::acceptFrame has a payload bounds check before memcpy."""
    src = _read_source(_INV_V2)

    assert "memcpy(core.beginHeader().ptr(), core.beginTail(0).ptr(), core.headerSize())" in src, \
        "expected memcpy pattern not found in InverterV2.cpp; file may have changed"

    has_guard = _has_tail_payload_guard(src, "memcpy(core.beginHeader")

    assert has_guard, (
        "V2 batcher memcpy lacks runtime frame-size bounds check — "
        "InverterV2::acceptFrame copies core.headerSize() bytes from tail region "
        "without verifying at least headerSize() bytes are available there"
    )

    assert _multiplication_is_64bit(src, "memcpy(core.beginHeader"), (
        "V2 batcher bounds-check multiplication is still in 32-bit arithmetic — "
        "count() * tailSize() can wrap on a crafted oversized batcher frame "
        "and the comparison would then under-approximate the required tail "
        "bytes; promote operands to uint64_t before the multiplication"
    )
