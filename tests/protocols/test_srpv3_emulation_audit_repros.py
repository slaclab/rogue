#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
# -----------------------------------------------------------------------------
# Description:
#   Audit repro tests for PROT-007 and PROT-012:
#   PROT-007 — SrpV3Emulation::allocatePage uses raw malloc(0x1000) with no
#              RAII; if the subsequent map insert throws after malloc, the
#              page leaks.
#   PROT-012 — Random-fill behaviour of new pages is documented only in the
#              .cpp comment, not in the public header docstring; callers
#              writing deterministic tests may be surprised.
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


def _extract_function_body(src, func_name):
    """Extract the lines of a named function from C++ source text.

    Scans for ``func_name`` and returns lines from that point to the
    matching closing brace.  Returns empty string if not found.
    """
    lines = src.splitlines()
    start = None
    for i, line in enumerate(lines):
        if func_name in line:
            start = i
            break
    if start is None:
        return ""
    depth = 0
    body_lines = []
    for line in lines[start:]:
        body_lines.append(line)
        depth += line.count("{") - line.count("}")
        if depth <= 0 and body_lines:
            break
    return "\n".join(body_lines)


def test_srpv3_emulation_page_uses_raii_prot_007():
    """PROT-007: SrpV3Emulation::allocatePage uses raw malloc without RAII wrapper.

    SrpV3Emulation.cpp allocates each 4 KiB emulated memory page via
    ``malloc(0x1000)`` and stores the raw pointer in ``pages_`` / ``memMap_``.
    The destructor walks the map calling ``free()``.  If the ``map::insert``
    throws ``std::bad_alloc`` after ``malloc`` succeeds, the page leaks because
    the raw pointer is not held by any RAII owner.  A correct implementation
    would use ``std::unique_ptr<uint8_t[]>`` or ``std::vector<uint8_t>`` so
    the page is freed on any exception path.
    """
    src = _EMULATION_CPP.read_text()

    # Confirm the raw malloc is still present
    assert "malloc(0x1000)" in src, \
        "PROT-007: malloc(0x1000) not found in SrpV3Emulation.cpp; file may have changed"

    # Scope the RAII check to just the allocatePage function body to avoid
    # false-positives from vector<uint8_t> used elsewhere in the file.
    alloc_body = _extract_function_body(src, "allocatePage")
    assert alloc_body, \
        "PROT-007: allocatePage function not found in SrpV3Emulation.cpp"

    # A RAII fix would replace malloc with std::unique_ptr or std::make_unique
    # inside the allocatePage function specifically.  std::vector<uint8_t> used
    # in processFrame for payload buffers does NOT fix the page-allocation leak.
    has_raii_in_alloc = any(
        pattern in alloc_body
        for pattern in (
            "std::unique_ptr<uint8_t",
            "std::make_unique<uint8_t",
            "unique_ptr<uint8_t",
            "make_unique<uint8_t",
        )
    )

    assert has_raii_in_alloc, (
        "PROT-007: SrpV3Emulation::allocatePage uses raw malloc(0x1000) without RAII; "
        "if memMap_.insert() throws after malloc the page leaks — "
        "replace with std::unique_ptr<uint8_t[]> or std::make_unique<uint8_t[]>(0x1000)"
    )


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


def test_srpv3_emulation_random_fill_documented_prot_012():
    """PROT-012: SrpV3Emulation random-fill init not in the class-level public docstring.

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
        "PROT-012: class-level docstring not found in SrpV3Emulation.h"

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
        "PROT-012: random-fill init mentioned in SrpV3Emulation.cpp and private allocatePage doc "
        "but NOT in the class-level public docstring of SrpV3Emulation.h; "
        "deterministic-test callers may be surprised by non-zero initial page contents — "
        "add a note about random fill to the class-level /** ... */ docstring in SrpV3Emulation.h"
    )
