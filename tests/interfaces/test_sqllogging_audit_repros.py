#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Audit repros for PYR-010, PYR-011, PYR-012.
#   PYR-010: SqlReader uses sqlalchemy.MetaData(engine) and autoload=True —
#            both APIs were removed in SQLAlchemy 2.0.
#   PYR-011: SqlReader.getVariable/getSyslog reference self._conn which is
#            never assigned in __init__; raises AttributeError on call.
#   PYR-012: SqlLogger._worker swallows DB exceptions silently; callers
#            have no way to detect the failure.
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import inspect

import pytest

pytest.importorskip("sqlalchemy")


# ---------------------------------------------------------------------------
# PYR-010 — SqlReader uses SQLAlchemy 1.x-only APIs
# ---------------------------------------------------------------------------
def test_sqlreader_uses_sqlalchemy_2_compatible_api_pyr_010():
    """PYR-010: SqlReader uses MetaData(engine) and autoload=True removed in SQLAlchemy 2.0."""
    import pyrogue.interfaces._SqlLogging as sql_mod

    src_reader = inspect.getsource(sql_mod.SqlReader)

    # MetaData(engine) — positional engine argument was removed in SA 2.0
    assert "MetaData(engine)" not in src_reader, (
        "PYR-010: SqlReader.__init__ calls sqlalchemy.MetaData(engine) "
        "with a positional engine argument; this API was removed in "
        "SQLAlchemy 2.0 and raises TypeError on modern installs"
    )

    # autoload=True on Table() — removed in SA 2.0
    assert "autoload=True" not in src_reader, (
        "PYR-010: SqlReader.__init__ passes autoload=True to sqlalchemy.Table(); "
        "this keyword was removed in SQLAlchemy 2.0"
    )


# ---------------------------------------------------------------------------
# PYR-011 — SqlReader.getVariable / getSyslog reference self._conn
# ---------------------------------------------------------------------------
def test_sqlreader_init_sets_conn_pyr_011():
    """PYR-011: SqlReader.__init__ never assigns self._conn; getVariable/getSyslog raise AttributeError."""
    import pyrogue.interfaces._SqlLogging as sql_mod

    init_src = inspect.getsource(sql_mod.SqlReader.__init__)

    assert "self._conn" in init_src, (
        "PYR-011: SqlReader.__init__ does not assign self._conn; "
        "getVariable() and getSyslog() will raise AttributeError when called "
        "because self._conn is never initialised"
    )


# ---------------------------------------------------------------------------
# PYR-012 — SqlLogger._worker swallows DB failures silently
# ---------------------------------------------------------------------------
def test_sqlworker_propagates_db_failure_pyr_012():
    """PYR-012: SqlLogger._worker silently swallows DB failures; no surface to callers."""
    import pyrogue.interfaces._SqlLogging as sql_mod

    worker_src = inspect.getsource(sql_mod.SqlLogger._worker)

    # After swallowing the exception the worker must expose failure state via
    # a public/semi-public attribute (e.g. _lastError) or re-raise.
    # On HEAD neither is present; the bare except sets self._engine = None and
    # continues, silently discarding all subsequent queued entries.
    exposes_failure = (
        "_lastError" in worker_src
        or "raise" in worker_src
        or "_error" in worker_src.lower()
    )

    assert exposes_failure, (
        "PYR-012: SqlLogger._worker silently swallows DB failure "
        "(bare `except Exception as e` sets self._engine=None and continues); "
        "callers have no observable signal that data is being dropped"
    )
