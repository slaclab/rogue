#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import importlib.util
import threading
import time
from pathlib import Path
from types import SimpleNamespace


def _load_virtual_client():
    module_path = Path(__file__).resolve().parents[2] / "python/pyrogue/interfaces/_Virtual.py"
    spec = importlib.util.spec_from_file_location("rogue_test_virtual_module", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.VirtualClient


VirtualClient = _load_virtual_client()


class _LogRecorder:
    def __init__(self):
        self.messages = []

    def warning(self, message):
        self.messages.append(message)


def _make_client(link_timeout=10.0, request_stall_timeout=None):
    client = VirtualClient.__new__(VirtualClient, "localhost", 9099)
    client._monitors = []
    client._root = SimpleNamespace(name="root")
    client._log = _LogRecorder()
    client._reqLock = threading.Lock()
    client._reqCount = 0
    client._reqSince = None
    client._ltime = time.time()
    client._link = True
    client._linkTimeout = link_timeout
    client._requestStallTimeout = request_stall_timeout
    return client


def test_virtual_client_stays_linked_while_request_is_pending():
    client = _make_client()
    states = []
    client._monitors.append(states.append)
    client._ltime = time.time() - 30.0
    client._requestStart()

    client._checkLinkState()

    assert client.linked is True
    assert states == []


def test_virtual_client_disconnects_after_idle_timeout():
    client = _make_client()
    states = []
    client._monitors.append(states.append)
    client._ltime = time.time() - 30.0

    client._checkLinkState()

    assert client.linked is False
    assert states == [False]


def test_virtual_client_successful_request_restores_link_state():
    client = _make_client()
    states = []
    client._monitors.append(states.append)
    client._link = False
    client._requestStart()

    client._requestDone(True)

    assert client.linked is True
    assert states == [True]


def test_virtual_client_declares_stalled_request_after_configured_timeout():
    client = _make_client(request_stall_timeout=5.0)
    states = []
    client._monitors.append(states.append)
    client._ltime = time.time() - 30.0
    client._requestStart()
    client._reqSince = time.time() - 6.0

    client._checkLinkState()

    assert client.linked is False
    assert states == [False]
