#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
# -----------------------------------------------------------------------------
# Description:
#   Regression tests
#   RSSI Controller::applicationRx() busy-loops with usleep(10)
#              for backpressure instead of using a condition variable.
#   rssi/Controller.cpp is a 979-line monolith; structural fragility
#              marker (line-count invariant).
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
_CONTROLLER_CPP = _REPO_ROOT / "src" / "rogue" / "protocols" / "rssi" / "Controller.cpp"


@pytest.mark.integration
def test_rssi_application_rx_uses_condvar():
    """applicationRx must not contain a usleep() busy-loop for backpressure.

    Controller.cpp originally spun on ``usleep(10)`` while
    ``txListCount_ >= curMaxBuffers_``, burning CPU until a transmit slot
    opened.  The fix replaced the spin with a ``std::condition_variable``
    wait_for so the thread blocks until signalled.  No other usleep() call
    exists in this file, so the absence of ``usleep(`` in the source is a
    strict regression guard.
    """
    src = _CONTROLLER_CPP.read_text()

    assert "usleep(" not in src, (
        "usleep() reintroduced in rssi/Controller.cpp; "
        "the fix replaced the applicationRx() busy-loop with a "
        "std::condition_variable wait_for under stMtx_, so the application "
        "thread blocks until a transmit slot is signalled rather than spinning"
    )
