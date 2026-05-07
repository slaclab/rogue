#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : ZmqClient / ZmqServer raw-thread ownership regression test
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
# Deterministic source-text repros for the ZmqClient / ZmqServer audit fixes:
#    -- ZmqClient ctor allocated thread_ via raw pointer
#    -- ZmqServer::start() allocated rThread_/sThread_ via raw pointers
#
# The fix moved both call sites to ``std::make_unique<std::thread>(...)`` so
# the worker handle is owned by a smart pointer and the catch-block rollback
# in ZmqServer::start() can safely ``reset()`` it without leaking.  Other
# thread-owning interfaces in the repo (e.g. ``memory::TcpClient``,
# ``memory::TcpServer``, ``stream::TcpCore``) still allocate raw
# ``std::thread*``; this file is *not* asserting a project-wide convention,
# only the specific change applied to the two ZMQ ctor/start sites.
#
# To avoid tripping on stray ``new std::thread`` mentions in unrelated
# comments or helpers, both regression tests extract the relevant function
# body and assert the positive invariant (``std::make_unique<std::thread>``
# present) inside that scope only.

import pathlib
import re

import pytest

import rogue.interfaces

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _read_src(relative_path):
    """Read a source file relative to repo root; skip if not a source checkout."""
    path = _REPO_ROOT / relative_path
    if not path.is_file():
        pytest.skip(
            f"Rogue source tree not available at {path}; this source-text "
            "audit repro only runs from a checkout, not from an installed "
            "package."
        )
    return path.read_text()


def _strip_cpp_comments_and_strings(src):
    """Replace C/C++ comments, string literals, and char literals with spaces."""
    out = []
    i = 0
    n = len(src)
    state = "code"  # code | line_comment | block_comment | string | char
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if state == "code":
            if c == "/" and nxt == "/":
                state = "line_comment"
                out.append("  ")
                i += 2
                continue
            if c == "/" and nxt == "*":
                state = "block_comment"
                out.append("  ")
                i += 2
                continue
            if c == '"':
                state = "string"
                out.append(" ")
                i += 1
                continue
            if c == "'":
                state = "char"
                out.append(" ")
                i += 1
                continue
            out.append(c)
            i += 1
            continue
        if state == "line_comment":
            if c == "\n":
                state = "code"
                out.append("\n")
            else:
                out.append(" ")
            i += 1
            continue
        if state == "block_comment":
            if c == "*" and nxt == "/":
                state = "code"
                out.append("  ")
                i += 2
                continue
            out.append("\n" if c == "\n" else " ")
            i += 1
            continue
        if state == "string":
            if c == "\\" and nxt:
                out.append("  ")
                i += 2
                continue
            if c == '"':
                state = "code"
                out.append(" ")
                i += 1
                continue
            out.append("\n" if c == "\n" else " ")
            i += 1
            continue
        if state == "char":
            if c == "\\" and nxt:
                out.append("  ")
                i += 2
                continue
            if c == "'":
                state = "code"
                out.append(" ")
                i += 1
                continue
            out.append("\n" if c == "\n" else " ")
            i += 1
            continue
    return "".join(out)


def _extract_body(src, signature_pattern):
    """Return the brace-delimited body of the first matching function definition."""
    match = re.search(signature_pattern, src)
    if match is None:
        return ""
    open_brace = src.find("{", match.end())
    if open_brace == -1:
        return ""
    depth = 0
    for i in range(open_brace, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[open_brace : i + 1]
    return ""


def test_zmq_client_ctor_uses_make_unique_thread():
    src = _strip_cpp_comments_and_strings(
        _read_src("src/rogue/interfaces/ZmqClient.cpp"))
    body = _extract_body(src, r"rogue::interfaces::ZmqClient::ZmqClient\s*\(")
    assert body, "could not locate ZmqClient ctor body in ZmqClient.cpp"
    assert "std::make_unique<std::thread>" in body, (
        "ZmqClient ctor must own thread_ via std::make_unique<std::thread>; "
        "raw `new std::thread` ownership broke exception-safety in the "
        "ctor's catch path."
    )
    assert "new std::thread" not in body, (
        "ZmqClient ctor still constructs thread_ with raw `new std::thread`; "
        "the audit fix mandates std::make_unique<std::thread> for this site."
    )


def test_zmq_server_start_uses_make_unique_thread():
    src = _strip_cpp_comments_and_strings(
        _read_src("src/rogue/interfaces/ZmqServer.cpp"))
    body = _extract_body(src, r"rogue::interfaces::ZmqServer::start\s*\(")
    assert body, "could not locate ZmqServer::start body in ZmqServer.cpp"
    assert body.count("std::make_unique<std::thread>") >= 2, (
        "ZmqServer::start() must allocate both rThread_ and sThread_ via "
        "std::make_unique<std::thread>; raw `new std::thread` made the "
        "rollback path leak the worker handle on a partial construction."
    )
    assert "new std::thread" not in body, (
        "ZmqServer::start() still constructs rThread_/sThread_ with raw "
        "`new std::thread`; the audit fix mandates std::make_unique<std::thread> "
        "for both worker allocations."
    )


def test_zmq_server_lifecycle_smoke(free_zmq_port):
    import pyrogue as pr

    root = pr.Root(name="AuditSmokeRoot", pollEn=False)
    root.start()
    try:
        srv = rogue.interfaces.ZmqServer("127.0.0.1", free_zmq_port)
        srv._stop()
    finally:
        root.stop()
