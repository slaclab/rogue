#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
# -----------------------------------------------------------------------------
# Description:
#   Regression tests guarding against historical bugs in
#   SrpV3Emulation::allocatePage:
#     - allocatePage previously used raw malloc(0x1000) with no RAII; if
#       the subsequent map insert threw after malloc, the page leaked.
#       The current implementation owns the page through
#       std::unique_ptr<uint8_t[]> and only releases ownership after a
#       successful insert.
#     - Random-fill behaviour of new pages used to be documented only in
#       the .cpp comment, not in the public header docstring; callers
#       writing deterministic tests could be surprised.  The class-level
#       Doxygen block in SrpV3Emulation.h must mention it.
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
_EMULATION_CPP = _REPO_ROOT / "src" / "rogue" / "protocols" / "srp" / "SrpV3Emulation.cpp"
_EMULATION_H = _REPO_ROOT / "include" / "rogue" / "protocols" / "srp" / "SrpV3Emulation.h"


def _extract_public_class_docstring(src):
    """Extract the class-level Doxygen block comment from the header.

    Returns the text of the block comment that immediately precedes
    the class declaration, which constitutes the public API documentation.
    """
    lines = src.splitlines()
    class_lineno = None
    for i, line in enumerate(lines):
        if line.strip().startswith("class ") and "SrpV3Emulation" in line:
            class_lineno = i
            break
    if class_lineno is None:
        return ""
    # Walk backwards to collect the preceding Doxygen block
    doc_lines = []
    in_block = False
    for line in reversed(lines[:class_lineno]):
        stripped = line.strip()
        if stripped.endswith("*/"):
            in_block = True
        if in_block:
            doc_lines.insert(0, line)
        if stripped.startswith("/**") and in_block:
            break
    return "\n".join(doc_lines)


def test_srpv3_emulation_random_fill_documented():
    """SrpV3Emulation random-fill init not in the class-level public docstring.

    New memory pages are filled with ``std::mt19937`` random data to emulate
    uninitialised hardware memory.  This behavioural contract is visible in a
    comment inside SrpV3Emulation.cpp and in the private ``allocatePage``
    docstring, but the **class-level** public API docstring (the block comment
    immediately before ``class SrpV3Emulation``) does not mention it.  Callers
    relying on the class-level docstring to understand read-back semantics
    (e.g., writing deterministic tests that assume zero-initialisation) will
    get random data and may see unexpected failures.
    """
    header_src = _EMULATION_H.read_text()
    class_doc = _extract_public_class_docstring(header_src)

    assert class_doc, \
        "class-level docstring not found in SrpV3Emulation.h"

    # The class-level docstring must mention random or non-deterministic fill
    has_random_note = any(
        keyword in class_doc.lower()
        for keyword in (
            "random",
            "uninitializ",
            "uninitialis",
            "non-deterministic",
            "nondeterministic",
        )
    )

    assert has_random_note, (
        "random-fill init mentioned in SrpV3Emulation.cpp and private allocatePage doc "
        "but NOT in the class-level public docstring of SrpV3Emulation.h; "
        "deterministic-test callers may be surprised by non-zero initial page contents — "
        "add a note about random fill to the class-level /**... */ docstring in SrpV3Emulation.h"
    )
