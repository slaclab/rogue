#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : memory::TcpClient / TcpServer raw-thread ownership regression test
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
#    -- memory::TcpClient ctor uses raw ``new std::thread``; should
#               use std::unique_ptr<std::thread>
#    -- memory::TcpServer ctor uses raw ``new std::thread``; same
#               tech-debt pattern
#
# These are integration-tier tests (they test transport-bound code paths)
# and are tagged @pytest.mark.integration per REP-03.  The source-text
# invariant pattern is fully deterministic.

import pathlib

import pytest

# Locate the repository root relative to this file:
#   tests/integration/<this file>  -> 3 levels up -> repo root
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.integration


def _read_src(relative_path: str) -> str:
    """Read a source file relative to the repository root."""
    return (_REPO_ROOT / relative_path).read_text()


def test_memory_tcpclient_uses_unique_ptr_thread():
    """memory::TcpClient ctor must NOT use raw ``new std::thread``.

    src/rogue/interfaces/memory/TcpClient.cpp line ~120 does::

        this->thread_ = new std::thread(&rim::TcpClient::runThread, this);

    The fix is to use std::unique_ptr<std::thread>.  Until the fix is applied
    this assertion fails deterministically.
    """
    src = _read_src("src/rogue/interfaces/memory/TcpClient.cpp")
    assert "new std::thread" not in src, (
        "memory TcpClient ctor uses raw new std::thread at line ~120; "
        "should be std::unique_ptr<std::thread>"
    )


def test_memory_tcpserver_uses_unique_ptr_thread():
    """memory::TcpServer ctor must NOT use raw ``new std::thread``.

    src/rogue/interfaces/memory/TcpServer.cpp line ~107 does::

        this->thread_ = new std::thread(&rim::TcpServer::runThread, this);

    The fix is to use std::unique_ptr<std::thread>.  Until the fix is applied
    this assertion fails deterministically.
    """
    src = _read_src("src/rogue/interfaces/memory/TcpServer.cpp")
    assert "new std::thread" not in src, (
        "memory TcpServer ctor uses raw new std::thread at line ~107; "
        "should be std::unique_ptr<std::thread>"
    )
