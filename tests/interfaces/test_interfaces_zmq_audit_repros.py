#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : ZmqClient / ZmqServer raw-thread ownership audit repros
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
#
# Deterministic source-text repros for:
#   IFCE-006 -- ZmqClient ctor uses raw ``new std::thread``
#   IFCE-007 -- ZmqServer::start() allocates threads with raw ``new std::thread``
#
# Pattern: read the production .cpp file and assert a structural property
# that HEAD violates.  Source-text tests are fully deterministic and require
# no timing or thread synchronisation.

import pathlib

import rogue.interfaces

# Locate the repository root relative to this file:
#   tests/interfaces/<this file>  -> 3 levels up -> repo root
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _read_src(relative_path):
    """Read a source file relative to the repository root."""
    return (_REPO_ROOT / relative_path).read_text()


def test_zmq_client_uses_unique_ptr_thread_ifce_006():
    # IFCE-006: ZmqClient ctor at src/rogue/interfaces/ZmqClient.cpp line ~173
    # allocates thread_ with raw "new std::thread".  The codebase norm is
    # std::unique_ptr<std::thread>.  Until the fix is applied this fails.
    src = _read_src("src/rogue/interfaces/ZmqClient.cpp")
    assert "new std::thread" not in src, (
        "IFCE-006: ZmqClient ctor uses raw new std::thread at line ~173; "
        "should use std::unique_ptr<std::thread>"
    )


def test_zmq_server_uses_unique_ptr_thread_ifce_007():
    # IFCE-007: ZmqServer::start() at src/rogue/interfaces/ZmqServer.cpp
    # lines ~114-115 allocates rThread and sThread with raw "new std::thread".
    # The fix is to use std::unique_ptr<std::thread> for both.
    src = _read_src("src/rogue/interfaces/ZmqServer.cpp")
    assert "new std::thread" not in src, (
        "IFCE-007: ZmqServer::start() allocates rThread and sThread with "
        "raw new std::thread; should use std::unique_ptr<std::thread>"
    )


def test_zmq_server_lifecycle_smoke(free_zmq_port):
    # Smoke: ZmqServer can be created and stopped without crashing.
    # Passes on HEAD; confirms the test file imports correctly.
    import pyrogue as pr

    root = pr.Root(name="AuditSmokeRoot", pollEn=False)
    root.start()
    try:
        srv = rogue.interfaces.ZmqServer("127.0.0.1", free_zmq_port, False)
        srv._stop()
    finally:
        root.stop()
