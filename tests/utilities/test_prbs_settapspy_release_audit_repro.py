#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Regression test.
#   Prbs::setTapsPy calls setTaps() between PyObject_GetBuffer and
#   PyBuffer_Release.  setTaps() now throws rogue::GeneralError on
#   allocation failure (the strong-exception-guarantee fix), so without
#   a try/catch around setTaps() the Py_buffer is leaked for the lifetime
#   of the interpreter on the OOM path.  This source-text audit-repro
#   asserts the throw-path Release is in place.
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
_PRBS_CPP = _REPO_ROOT / "src" / "rogue" / "utilities" / "Prbs.cpp"


def test_prbs_settapspy_releases_pybuffer_on_throw():
    """Prbs::setTapsPy must Release the Py_buffer on the setTaps throw path."""
    src = _PRBS_CPP.read_text()

    # Locate the body of setTapsPy.
    match = re.search(
        r"void\s+ru::Prbs::setTapsPy\([^)]*\)\s*\{(?P<body>.*?)\n\}\s*\n",
        src,
        re.DOTALL,
    )
    assert match is not None, (
        "could not locate ru::Prbs::setTapsPy body in Prbs.cpp; the function "
        "may have been renamed or removed"
    )

    body = match.group("body")
    assert "PyObject_GetBuffer(" in body, (
        "expected PyObject_GetBuffer call in Prbs::setTapsPy"
    )
    assert "setTaps(" in body, (
        "expected setTaps() call in Prbs::setTapsPy"
    )

    # The setTaps() call (which can throw) must be wrapped in a try/catch
    # that calls PyBuffer_Release before re-raising.  Without this the
    # Py_buffer is leaked for the lifetime of the interpreter on the OOM
    # path that setTaps() now exposes.
    assert "try {" in body and "catch" in body and "PyBuffer_Release(&pyBuf)" in body, (
        "Prbs::setTapsPy does not release the Py_buffer on the setTaps "
        "throw path; setTaps() can throw rogue::GeneralError on OOM and "
        "would leak the Py_buffer for the lifetime of the interpreter"
    )

    # Pin the structural shape: the Release inside the catch must come
    # before the ``throw;`` re-raise.
    catch_match = re.search(
        r"catch\s*\(\.\.\.\)\s*\{(?P<catch>.*?)\}",
        body,
        re.DOTALL,
    )
    assert catch_match is not None, (
        "expected catch (...) block around setTaps in Prbs::setTapsPy"
    )
    catch_body = catch_match.group("catch")
    assert "PyBuffer_Release(&pyBuf)" in catch_body and "throw;" in catch_body, (
        "Prbs::setTapsPy catch block must Release the Py_buffer and then "
        "re-throw; the current shape risks losing the Py_buffer"
    )
