#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""Shared fixtures and helpers for scripts/repro/ sanitizer harness.

Local-to-scripts/repro/ conftest (per CONTEXT.md D-21). Intentionally
self-contained and does NOT reach into the tests/ tree — the two test
trees are isolated so rogue_ci.yml and sanitizer workflows can evolve
independently.

Exports:
    stress_iters (fixture, session-scoped) — reads ROGUE_STRESS_ITERS env
        var with default 1000. Cluster scripts use this to scale their
        inner-loop iteration count.
    skip_on_macos (pytest.mark.skipif) — decorator for cluster scripts that
        exercise RSSI/UDP loopback paths; macOS timing is too tight for the
        default RSSI retransmission budget (PROTO-RSSI-006).
    memory_root (fixture) — function-scoped _MemoryRoot instance for cluster
        scripts that need a PyRogue Root with a local memory emulator.
"""
import os
import sys

import pytest
import pyrogue as pr
import rogue.interfaces.memory


# ---- stress_iters fixture (D-21) ------------------------------------------

@pytest.fixture(scope="session")
def stress_iters():
    """Inner-loop iteration count for stress cluster scripts.

    Reads ROGUE_STRESS_ITERS env var (default 1000 per CONTEXT.md D-05).
    Session-scoped so the env var is read once per pytest invocation.
    """
    return int(os.environ.get("ROGUE_STRESS_ITERS", "1000"))


# ---- skip_on_macos decorator (PROTO-RSSI-006) -----------------------------

skip_on_macos = pytest.mark.skipif(
    sys.platform == "darwin",
    reason="RSSI/UDP loopback timing too tight on macOS (PROTO-RSSI-006)"
)


# ---- _MemoryRoot helper + memory_root fixture (D-21) ----------------------
# Intentional underscore prefix: this is the repro-local copy, NOT the
# canonical tests/conftest.py MemoryRoot. Duplicating (not importing) the
# pattern keeps the two test trees isolated per D-21.

class _MemoryRoot(pr.Root):
    def __init__(self, *, mem_width=4, mem_size=0x4000, **kwargs):
        super().__init__(pollEn=False, **kwargs)
        self._mem = rogue.interfaces.memory.Emulate(mem_width, mem_size)
        self.addInterface(self._mem)


@pytest.fixture
def memory_root():
    """Function-scoped PyRogue Root with a local memory emulator.

    Cluster scripts that need to exercise memory transactions (e.g.
    stress_memory_sub_transaction.py) request this fixture by name.
    """
    root = _MemoryRoot(name="root")
    with root:
        yield root


# ---- memory_root_unstarted fixture (CR-01 fix) ----------------------------
# Tests that need to `.add(Device)` children after fixture injection MUST use
# this fixture rather than `memory_root` above. pyrogue._Node.add() at
# python/pyrogue/_Node.py:334-336 raises NodeError when called on a started
# Root (where `self._root is not None`). This fixture yields an un-started
# Root; the test drives its own `with root:` block AFTER children are added.
#
# Canonical usage (mirrors stress_bsp_gil.py::test_stress_bsp_gilless_attribute):
#
#     def test_something(memory_root_unstarted):
#         root = memory_root_unstarted
#         root.add(_Probe(name="probe"))  # .add() BEFORE start
#         with root:                      # now start
#             # ... threaded stress body against root.probe ...

@pytest.fixture
def memory_root_unstarted():
    """Function-scoped un-started _MemoryRoot.

    The fixture does NOT enter `with root:`. Tests receive a fresh Root with
    the memory Emulate slave attached as an interface but with no children
    added yet. The test must add children before entering its own
    `with root:` block. Teardown is implicit: if the test entered `with root:`,
    Root.__exit__ already ran; if the test body raised before entering, the
    Root is still unstarted and no cleanup is required.

    See 02-REVIEW.md CR-01 and 02-10-PLAN.md for background on why Option (b)
    (add-a-new-fixture) was chosen over Option (a) (change memory_root contract):
    preserving the existing memory_root fixture keeps stress_memory_sub_transaction.py
    untouched, which is the minimum-surgical-change principle.
    """
    root = _MemoryRoot(name="root")
    yield root
