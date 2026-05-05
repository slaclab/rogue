#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
# -----------------------------------------------------------------------------
# Description:
#   Regression tests
#   SrpV0::acceptFrame expired-transaction branch previously called
#   log_->warning() and continued without calling tran->error(), leaving
#   the Transaction pending indefinitely instead of completing it with
#   an error.
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

import pytest


_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SRPV0 = _REPO_ROOT / "src" / "rogue" / "protocols" / "srp" / "SrpV0.cpp"


@pytest.mark.integration
def test_srpv0_calls_tran_error_on_timeout():
    """SrpV0::acceptFrame expired-transaction branch must call tran->error().

    SrpV0.cpp handles expired transactions inside ``acceptFrame()`` (the
    incoming-frame path that reacquires the Transaction by id).  The branch
    that detects ``tran->expired()`` previously logged a warning and returned
    without calling ``tran->error(...)``, so the Transaction was left pending.
    Compare with SrpV3.cpp which calls ``tran->error("Timeout")`` on the
    equivalent path.  Without the error() call any Block waiting on the
    transaction's completion future will block forever.
    """
    src = _SRPV0.read_text()
    lines = src.splitlines()

    # Find the expired() check
    expired_lineno = None
    for i, line in enumerate(lines):
        if "tran->expired()" in line or "expired()" in line:
            expired_lineno = i
            break

    assert expired_lineno is not None, \
        "tran->expired() check not found in SrpV0.cpp; file may have changed"

    # Inspect the block following expired() for a tran->error( call.
    # Search up to 15 lines after the expired() check.
    search_end = min(len(lines), expired_lineno + 15)
    following = "\n".join(lines[expired_lineno:search_end])

    has_error_call = "tran->error(" in following or "->error(" in following

    assert has_error_call, (
        "SrpV0::acceptFrame expired-transaction branch lacks tran->error() call "
        "(compare with SrpV3.cpp which calls tran->error(\"Timeout\") on the equivalent path); "
        "Transaction left pending indefinitely — callers waiting on the transaction future hang forever"
    )
