#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Regression test.
#   Block::setPyFunc calls setBytes() between PyObject_GetBuffer and
#   PyBuffer_Release in both the list-variable branch and the scalar
#   branch.  setBytes() can throw rogue::GeneralError (index out of
#   range, malloc OOM in the byteReverse path), so without a try/catch
#   that releases the Py_buffer before re-raising, the Py_buffer is
#   leaked for the lifetime of the interpreter on the throw path.
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import pathlib
import re


_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_BLOCK_CPP = _REPO_ROOT / "src" / "rogue" / "interfaces" / "memory" / "Block.cpp"


def _setpyfunc_body():
    src = _BLOCK_CPP.read_text()

    match = re.search(
        r"void\s+rim::Block::setPyFunc\([^)]*\)\s*\{(?P<body>.*?)\n\}\s*\n",
        src,
        re.DOTALL,
    )
    assert match is not None, (
        "could not locate rim::Block::setPyFunc body in Block.cpp; the "
        "function may have been renamed or removed"
    )
    return match.group("body")


def test_block_setpyfunc_releases_pybuffer_on_throw():
    """Both setBytes call sites in setPyFunc must Release the Py_buffer on throw."""
    body = _setpyfunc_body()

    # We want every setBytes call inside setPyFunc to be wrapped by a
    # try/catch that releases the Py_buffer before re-raising.  Match
    # the actual call expression (not the bare token, which would also
    # appear in narrative comments).
    setbytes_calls = re.findall(
        r"setBytes\(reinterpret_cast<uint8_t\*>\(valueBuf\.buf\)",
        body,
    )
    assert len(setbytes_calls) >= 2, (
        f"expected at least 2 setBytes call sites in setPyFunc (list + "
        f"scalar branches); found {len(setbytes_calls)}"
    )

    catch_blocks = re.findall(
        r"catch\s*\(\.\.\.\)\s*\{[^}]*PyBuffer_Release\(&valueBuf\)[^}]*throw;\s*\}",
        body,
        re.DOTALL,
    )
    assert len(catch_blocks) >= len(setbytes_calls), (
        "Block::setPyFunc has setBytes() call sites without a "
        "PyBuffer_Release-then-throw catch block; setBytes() can throw "
        "(index out of range, byteReverse malloc OOM) and would leak the "
        "Py_buffer for the lifetime of the interpreter on the throw path "
        f"(found {len(setbytes_calls)} setBytes calls, "
        f"{len(catch_blocks)} qualifying catch blocks)"
    )


def test_block_setbytearraypy_releases_pybuffer_on_throw():
    """setByteArrayPy must Release the Py_buffer on the setBytes throw path.

    setByteArrayPy follows the same PyObject_GetBuffer -> setBytes ->
    PyBuffer_Release pattern as setPyFunc, with the same throw-path leak
    if setBytes() raises (out-of-range index, byteReverse malloc OOM).
    """
    src = _BLOCK_CPP.read_text()
    match = re.search(
        r"void\s+rim::Block::setByteArrayPy\([^)]*\)\s*\{(?P<body>.*?)\n\}\s*\n",
        src,
        re.DOTALL,
    )
    assert match is not None, (
        "could not locate rim::Block::setByteArrayPy body in Block.cpp"
    )
    body = match.group("body")

    assert "setBytes(reinterpret_cast<uint8_t*>(valueBuf.buf)" in body, (
        "expected setBytes call site in setByteArrayPy"
    )

    catch_blocks = re.findall(
        r"catch\s*\(\.\.\.\)\s*\{[^}]*PyBuffer_Release\(&valueBuf\)[^}]*throw;\s*\}",
        body,
        re.DOTALL,
    )
    assert catch_blocks, (
        "Block::setByteArrayPy lacks a PyBuffer_Release-then-throw catch "
        "around setBytes(); setBytes() can throw (index out of range, "
        "byteReverse malloc OOM) and would leak the Py_buffer for the "
        "lifetime of the interpreter on the throw path"
    )
