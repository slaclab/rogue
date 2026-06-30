#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   pytest fixtures shared by tests under tests/protocols/ (currently the
#   session-scoped rxe_server fixture for hardware-gated RoCEv2 tests).
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import logging

import pytest


# ---------------------------------------------------------------------------
# Re-export of wait_for + MemoryRoot from tests/conftest.py.
#
# pytest-xdist `--dist loadfile` can assign ONE worker both a
# tests/protocols/test_*.py file and a tests/utilities/test_prbs*.py file.
# With pytest's default importmode=prepend, the last conftest discovered
# wins sys.path[0], which can make a bare `from conftest import wait_for`
# in a utilities test resolve to THIS file instead of tests/conftest.py.
#
# To keep those bare imports working regardless of worker layout, we load
# tests/conftest.py explicitly by absolute path under a distinct module
# name and re-publish the two helpers used by sibling test trees. The
# importlib-loaded copy is ONLY used as a symbol source: pytest's own
# fixture registration still happens through its normal path-based
# conftest discovery, so we do not duplicate fixtures.
# ---------------------------------------------------------------------------
import importlib.util as _importlib_util
import pathlib as _pathlib

_ROOT_CONFTEST_PATH = _pathlib.Path(__file__).resolve().parent.parent / "conftest.py"
_spec = _importlib_util.spec_from_file_location(
    "_tests_root_conftest", _ROOT_CONFTEST_PATH
)
_root_conftest = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_root_conftest)

wait_for = _root_conftest.wait_for
MemoryRoot = _root_conftest.MemoryRoot


@pytest.fixture(scope="session")
def rxe_server():
    """Session-scoped live rxe0 Server — one ibverbs device open per session.
    Skips the test if rxe0 is not available (never silently passes).
    Teardown is unconditional via try/finally in the yield pattern."""
    import rogue.protocols.rocev2 as _r
    # Args: deviceName, ibPort, gidIndex, maxPayload, rxQueueDepth
    # (9000/256 match RoCEv2Server defaults).
    try:
        server = _r.Server.create("rxe0", 1, 0, 9000, 256)
    except Exception as e:
        pytest.skip(f"rxe0 not available for session-scoped fixture: {e}")
    try:
        yield server
    finally:
        # Swallow stop() exceptions during teardown so we never mask
        # the original test failure or KeyboardInterrupt.
        try:
            server.stop()
        except Exception as e:
            logging.getLogger("rocev2.teardown").warning(
                "server.stop() failed during fixture teardown: %s", e)
