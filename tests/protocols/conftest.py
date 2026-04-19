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

# Metadata-bus layout constants — used by the response-word helpers below.
# Mirrors the subset of constants imported by tests/protocols/test_rocev2.py
# for the same helpers; co-locate the import so the helpers are self-contained
# when multiple test files consume them via conftest.
from pyrogue.protocols._RoCEv2 import (
    _METADATA_PD_T,
    _METADATA_MR_T,
    _METADATA_QP_T,
    _MR_KEY_B,
    _IBV_QPS_RTS,
)


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


# ---------------------------------------------------------------------------
# Metadata-bus response-word builders — shared by all tests in tests/protocols/.
#
# Each _pack_<type>_ok returns a 276-bit RX-bus word that satisfies the
# corresponding _decode_<type>_resp in _RoCEv2.py. The _fail variants clear
# ONLY the success bit, leaving every other field identical to the _ok word.
# _pack_unknown_type emits a word whose resp_type tag is 3 (reserved) so the
# "expected PD/MR/QP response, got type=3" branches in _roce_setup_connection
# can be exercised without touching production code.
#
# These are NOT pytest fixtures — they are plain module-level functions.
# Tests import them explicitly: `from conftest import _pack_pd_ok`.
# (pytest adds the conftest.py directory to sys.path at collection time, so
# the bare `conftest` import works without a package __init__.py.)
# ---------------------------------------------------------------------------


def _pack_pd_ok(pd_handler=0xDEADBEEF):
    """RX word: PD response, success=1, pd_handler payload.

    Matches _decode_pd_resp in _RoCEv2.py. resp_type tag at
    bits [275:274]; success bit at bit 64; pd_handler at [63:32].
    """
    return ((_METADATA_PD_T & 0x3) << 274) | (1 << 64) | (pd_handler << 32)


def _pack_mr_ok(lkey=0xABCD1234, rkey=0x5678DEAD):
    """RX word: MR response, success=1, lkey/rkey payload.

    Matches _decode_mr_resp in _RoCEv2.py. resp_type tag at
    bits [275:274]; success bit at bit 262; lkey at [63:32]; rkey at [31:0].
    """
    return ((_METADATA_MR_T & 0x3) << 274) | (1 << 262) | (lkey << _MR_KEY_B) | rkey


def _pack_qp_ok(qpn=0x123456, state=_IBV_QPS_RTS):
    """RX word: QP response, success=1, qpn + qp_state payload.

    Matches _decode_qp_resp in _RoCEv2.py. resp_type tag at
    bits [275:274]; success bit at bit 273; qpn at [272:249];
    qp_state at [216:213].
    """
    return ((_METADATA_QP_T & 0x3) << 274) | (1 << 273) | (qpn << 249) | (state << 213)


# ---------------------------------------------------------------------------
# Symmetric failure variants — identical to _ok except the success bit is
# cleared.
# ---------------------------------------------------------------------------


def _pack_pd_fail(pd_handler=0xDEADBEEF):
    """RX word: PD response, success=0, pd_handler payload preserved.

    Identical to _pack_pd_ok except the success bit at bit 64 is 0.
    Mirrors _roce_setup_connection's "FPGA PD allocation failed" branch.
    """
    return ((_METADATA_PD_T & 0x3) << 274) | (0 << 64) | (pd_handler << 32)


def _pack_mr_fail(lkey=0xABCD1234, rkey=0x5678DEAD):
    """RX word: MR response, success=0, lkey/rkey payload preserved.

    Identical to _pack_mr_ok except the success bit at bit 262 is 0.
    Simulates FPGA MR allocation failure (the 'FPGA MR allocation failed'
    branch in _roce_setup_connection).
    """
    return ((_METADATA_MR_T & 0x3) << 274) | (0 << 262) | (lkey << _MR_KEY_B) | rkey


def _pack_qp_fail(qpn=0x123456, state=_IBV_QPS_RTS):
    """RX word: QP response, success=0, qpn + state payload preserved.

    Identical to _pack_qp_ok except the success bit at bit 273 is 0.
    """
    return ((_METADATA_QP_T & 0x3) << 274) | (0 << 273) | (qpn << 249) | (state << 213)


# ---------------------------------------------------------------------------
# Reserved-tag builder — resp_type=3 is the unused 2-bit value (PD=0, MR=1,
# QP=2 are the named values). Drives the "actual_type != _METADATA_*_T"
# raise paths in _roce_setup_connection.
# ---------------------------------------------------------------------------


def _pack_unknown_type():
    """RX word with resp_type tag = 3 (reserved / unused) and every other
    field zeroed. Causes _decode_resp_type(rx) == 3 — every named decoder's
    type-check branch in _roce_setup_connection raises rogue.GeneralError
    with 'Expected PD/MR/QP response, got type=3'.
    """
    return (0x3 << 274)
