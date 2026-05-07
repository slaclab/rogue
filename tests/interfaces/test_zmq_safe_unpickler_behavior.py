#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : ZmqServer _SafeUnpickler / _safe_loads behavior
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
# Behavioral coverage for the restricted ``Unpickler`` that
# ``ZmqServer._doRequest`` funnels incoming binary requests through.
#
# The tests here exercise the actual deserialisation path so a regression
# that keeps ``_safe_loads`` in place but quietly relaxes the allowlist
# still fails. End-to-end ``_doRequest`` coverage lives in
# ``test_zmq_do_request_behavior.py``.

import io
import os
import pickle
import subprocess

import numpy as np
import pytest

from pyrogue.interfaces._ZmqServer import _SafeUnpickler, _safe_loads


def _ndarray_pickle_globals():
    """Return the (module, name) pairs an ndarray pickle resolves at load time."""
    seen = []

    class _Tracking(pickle.Unpickler):
        def find_class(self, module, name):
            seen.append((module, name))
            return super().find_class(module, name)

    _Tracking(io.BytesIO(pickle.dumps(np.arange(2, dtype=np.uint8)))).load()
    return seen


def test_safe_loads_round_trips_simpleclient_shaped_payload():
    payload = pickle.dumps({
        'attr': 'set',
        'path': '/Foo.Bar',
        'args': (1, 2.5, 'x', None, True, b'raw'),
        'kwargs': {'mask': 0xFF, 'verify': False},
    })
    obj = _safe_loads(payload)
    assert obj['attr'] == 'set'
    assert obj['path'] == '/Foo.Bar'
    assert obj['args'] == (1, 2.5, 'x', None, True, b'raw')
    assert obj['kwargs'] == {'mask': 0xFF, 'verify': False}


def test_safe_loads_round_trips_numpy_ndarray():
    arr = np.arange(8, dtype=np.uint32)
    obj = _safe_loads(pickle.dumps(arr))
    assert isinstance(obj, np.ndarray)
    assert obj.dtype == np.uint32
    np.testing.assert_array_equal(obj, arr)


def test_safe_loads_rejects_os_system():
    with pytest.raises(pickle.UnpicklingError, match="Unsafe pickle payload"):
        _safe_loads(pickle.dumps(os.system))


def test_safe_loads_rejects_subprocess_popen():
    with pytest.raises(pickle.UnpicklingError, match="Unsafe pickle payload"):
        _safe_loads(pickle.dumps(subprocess.Popen))


def test_safe_loads_rejects_builtin_eval():
    with pytest.raises(pickle.UnpicklingError, match="Unsafe pickle payload"):
        _safe_loads(pickle.dumps(eval))


def test_safe_unpickler_find_class_rejects_unlisted_module():
    unp = _SafeUnpickler(io.BytesIO(b''))
    with pytest.raises(pickle.UnpicklingError, match="Unsafe pickle payload"):
        unp.find_class('os', 'system')
    with pytest.raises(pickle.UnpicklingError, match="Unsafe pickle payload"):
        unp.find_class('builtins', 'exec')


def test_safe_unpickler_find_class_accepts_numpy_submodules():
    pairs = _ndarray_pickle_globals()
    assert pairs, "ndarray pickle resolved no globals; environment is broken"
    unp = _SafeUnpickler(io.BytesIO(b''))
    for module, name in pairs:
        cls = unp.find_class(module, name)
        assert callable(cls), (
            f"_SafeUnpickler.find_class refused {module}.{name}, which the "
            "running numpy build needs to reconstruct an ndarray; the "
            "_ALLOWED_TOP_PACKAGES gate must keep admitting numpy submodules."
        )
