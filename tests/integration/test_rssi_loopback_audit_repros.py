#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
# -----------------------------------------------------------------------------
# Description:
#   Audit repro tests for PROT-015 and PROT-019:
#   PROT-015 — RSSI Controller::applicationRx() busy-loops with usleep(10)
#              for backpressure instead of using a condition variable.
#   PROT-019 — rssi/Controller.cpp is a 979-line monolith; structural fragility
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

# Line-count threshold above which the file is considered a fragility risk.
_MONOLITH_THRESHOLD = 600


@pytest.mark.integration
def test_rssi_application_rx_uses_condvar_prot_015():
    """PROT-015: RSSI Controller::applicationRx uses busy-loop usleep(10) for backpressure.

    Controller.cpp implements flow-control backpressure in applicationRx() by
    spinning on ``usleep(10)`` while ``txListCount_ >= curMaxBuffers_``.  There is
    no condition-variable wakeup when a transmit slot opens — the thread polls
    continuously, burning CPU.  A correct implementation would use
    ``std::condition_variable::wait_for`` (or ``wait``) to block until signalled
    by the thread that consumes a transmit slot.
    """
    src = _CONTROLLER_CPP.read_text()

    # Confirm the busy-loop pattern is present
    assert "usleep" in src, \
        "PROT-015: usleep not found in Controller.cpp; file may have changed"

    # A cv-based fix would remove usleep from the backpressure path and replace
    # it with a condition variable wait.  Check that usleep is no longer used
    # in the flow-control loop.
    lines = src.splitlines()

    # Find the backpressure while-loop
    busyloop_lineno = None
    for i, line in enumerate(lines):
        if "usleep" in line:
            busyloop_lineno = i
            break

    assert busyloop_lineno is not None, \
        "PROT-015: usleep line not found; Controller.cpp may have changed"

    # Search context around the usleep for a wait/notify pattern
    search_start = max(0, busyloop_lineno - 15)
    search_end = min(len(lines), busyloop_lineno + 5)
    context = "\n".join(lines[search_start:search_end])

    has_condvar = any(
        token in context
        for token in (
            "wait_for",
            "wait(",
            "notify_one",
            "notify_all",
            "condition_variable",
            "cond_",
            "cv_",
        )
    )

    assert has_condvar, (
        "PROT-015: applicationRx uses busy-loop usleep(10) for backpressure; "
        "should use cv.wait_for so the thread blocks until a transmit slot opens "
        "rather than spinning and burning CPU"
    )


@pytest.mark.integration
def test_rssi_controller_below_size_threshold_prot_019():
    """PROT-019: Controller.cpp is a 979-line monolith (threshold: 600 lines).

    rssi/Controller.cpp is a single-file implementation of the full RSSI state
    machine, retransmit logic, flow control, out-of-order queue, and timer
    management.  At 979 lines any change risks unintended interaction between
    subsystems.  This marker test fails while the file remains above the
    refactoring threshold.
    """
    lines = _CONTROLLER_CPP.read_text().splitlines()
    actual = len(lines)

    msg = (
        "PROT-019: Controller.cpp is "
        + str(actual)
        + " lines (>"
        + str(_MONOLITH_THRESHOLD)
        + "); should be split for maintainability - "
        "state machine, retransmit, flow control, OOO queue, "
        "and timer management all live in a single 979-line file"
    )
    assert actual < _MONOLITH_THRESHOLD, msg
