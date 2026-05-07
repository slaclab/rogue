#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Behavioral tests for ``ZmqServer._doRequest`` itself.
#
#   The companion suites cover adjacent layers:
#     * ``test_zmq_safe_unpickler_behavior.py`` exercises ``_safe_loads`` /
#       ``_SafeUnpickler`` directly.
#     * ``test_zmq_pickle_payload_audit_repro.py`` walks the AST of
#       ``_doRequest`` and rejects any reference to ``pickle.loads`` /
#       ``_pickle.loads`` / ``pickle.load`` / ``_pickle.load`` /
#       ``pickle.Unpickler`` / ``_pickle.Unpickler``.
#
#   Neither layer catches a regression that imports a raw loader as a bare
#   name -- ``from pickle import loads; loads(data)``.  The AST audit only
#   sees ``Attribute(value=Name)`` references; ``loads`` here is just a
#   ``Name``.  The unpickler-level tests never invoke ``_doRequest`` at all.
#
#   These tests close that gap: they feed crafted payloads through
#   ``_doRequest`` end-to-end and assert (a) ``_doOperation`` is never
#   reached for an unsafe pickle, (b) the response is a pickled Exception
#   whose message contains "Unsafe pickle payload" -- which only
#   ``_SafeUnpickler.find_class`` produces -- and (c) for REDUCE-driven
#   payloads the embedded callable is never invoked.  Each property fails
#   under the bare-import regression above, so any future bypass that
#   re-routes the bytes around ``_safe_loads`` is caught here.
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import os
import pickle
import subprocess

import pyrogue.interfaces._ZmqServer as zmq_server_mod


# Stays empty if _SafeUnpickler blocks the REDUCE global; grows if bypassed.
_REDUCE_MARKER = []


def _record_pwn(*args, **kwargs):
    """REDUCE-target marker; must never run during unpickling."""
    _REDUCE_MARKER.append((args, kwargs))
    return args


class _PwnReduce:
    """Pickling this object emits a REDUCE that calls ``_record_pwn``."""

    def __reduce__(self):
        return (_record_pwn, (b'pwned',))


class _FakeRoot:
    def addVarListener(self, **_):
        pass


def _make_server(monkeypatch):
    """Construct a ZmqServer skipping the C++ ctor (which would bind ZMQ
    ports) and the variable-listener wiring."""
    monkeypatch.setattr(
        zmq_server_mod.rogue.interfaces.ZmqServer,
        "__init__",
        lambda self, addr, port: setattr(self, "_port", port),
    )
    return zmq_server_mod.ZmqServer(
        root=_FakeRoot(), addr="127.0.0.1", port=0)


def test_do_request_round_trips_benign_payload(monkeypatch):
    """Sanity: a dict-shaped request reaches _doOperation and the result
    pickles back."""
    server = _make_server(monkeypatch)

    captured = []

    def _op(d):
        captured.append(d)
        return {"ok": d.get("attr")}

    server._doOperation = _op

    request = pickle.dumps(
        {"path": "/Foo", "attr": "set", "args": (1,), "kwargs": {}})
    response = server._doRequest(request)

    assert isinstance(response, bytes)
    assert pickle.loads(response) == {"ok": "set"}
    assert captured == [
        {"path": "/Foo", "attr": "set", "args": (1,), "kwargs": {}}]


def test_do_request_rejects_pickled_os_system(monkeypatch):
    """A pickled os.system reference must be rejected at deserialise."""
    server = _make_server(monkeypatch)
    invoked = []
    server._doOperation = lambda d: invoked.append(d) or None

    response = server._doRequest(pickle.dumps(os.system))

    assert invoked == [], (
        "ZmqServer._doRequest let an os.system pickle through to "
        "_doOperation; the restricted Unpickler must reject the global "
        "before the REDUCE opcode can resolve it.  This usually means "
        "the request bytes are no longer routed through _safe_loads "
        "(e.g. a `from pickle import loads; loads(data)` regression).")

    decoded = pickle.loads(response)
    assert isinstance(decoded, Exception)
    assert "Unsafe pickle payload" in str(decoded), (
        f"Expected 'Unsafe pickle payload' in response, got: {decoded!r}. "
        "Only _SafeUnpickler.find_class produces that string, so a "
        "different exception means _doRequest stopped funnelling through "
        "_safe_loads.")


def test_do_request_rejects_pickled_subprocess_popen(monkeypatch):
    server = _make_server(monkeypatch)
    invoked = []
    server._doOperation = lambda d: invoked.append(d) or None

    response = server._doRequest(pickle.dumps(subprocess.Popen))

    assert invoked == []
    decoded = pickle.loads(response)
    assert isinstance(decoded, Exception)
    assert "Unsafe pickle payload" in str(decoded)


def test_do_request_rejects_pickled_eval_builtin(monkeypatch):
    """``eval`` lives in builtins but is not on the per-name allowlist."""
    server = _make_server(monkeypatch)
    invoked = []
    server._doOperation = lambda d: invoked.append(d) or None

    response = server._doRequest(pickle.dumps(eval))

    assert invoked == []
    decoded = pickle.loads(response)
    assert isinstance(decoded, Exception)
    assert "Unsafe pickle payload" in str(decoded)


def test_do_request_blocks_reduce_callable_before_execution(monkeypatch):
    """REDUCE-driven payload: the embedded callable must never run."""
    server = _make_server(monkeypatch)
    invoked = []
    server._doOperation = lambda d: invoked.append(d) or None

    _REDUCE_MARKER.clear()
    response = server._doRequest(pickle.dumps(_PwnReduce()))

    assert _REDUCE_MARKER == [], (
        f"REDUCE callable was invoked during unpickling; _SafeUnpickler "
        f"must refuse the global in find_class() before the opcode fires. "
        f"Marker history: {_REDUCE_MARKER}")
    assert invoked == []
    decoded = pickle.loads(response)
    assert isinstance(decoded, Exception)
    assert "Unsafe pickle payload" in str(decoded)
