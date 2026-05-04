#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""_iterateDict eval injection repro.

`nodeMatch` in python/pyrogue/_Node.py calls _iterateDict which calls
eval(f'tmpList[{keys[0]}]') where keys[0] comes directly from the
caller-supplied node path string. A path bracket expression containing
arbitrary Python code executes that code. This test confirms the injection
on HEAD using os.getenv as a side-effect sentinel.
"""

import os

import pyrogue as pr


class VarDevice(pr.Device):
    """Device with indexed LocalVariables so nodeMatch exercises the
    slice/eval branch for bracket-style lookups."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for i in range(4):
            self.add(pr.LocalVariable(name=f'Var[{i}]', value=0))


class NodeEvalRoot(pr.Root):
    def __init__(self):
        super().__init__(name='root', pollEn=False)
        self.add(VarDevice(name='Dev'))


def test_iterate_dict_eval_injection(monkeypatch):
    """Verify that nodeMatch/_iterateDict does NOT execute arbitrary code.

    On HEAD, eval(f'tmpList[{keys[0]}]') is called with user-controlled
    content. This test patches os.getenv to track calls, then passes a
    bracket expression containing __import__('os').getenv('USER') to
    nodeMatch. The assertion fires when the injection succeeds (os.getenv
    was invoked), confirming the  eval injection bug.
    """
    sentinel = 'AUDIT_REP_CORE_009_SENTINEL'
    monkeypatch.setenv('USER', sentinel)

    original_getenv = os.getenv
    getenv_calls = []

    def tracking_getenv(key, *args, **kwargs):
        getenv_calls.append(key)
        return original_getenv(key, *args, **kwargs)

    monkeypatch.setattr(os, 'getenv', tracking_getenv)

    with NodeEvalRoot() as root:
        payload = "__import__('os').getenv('USER')"
        try:
            root.Dev.nodeMatch(f'Var[{payload}]')
        except Exception:
            pass  # TypeError or similar from invalid index is expected

    assert 'USER' not in getenv_calls, (
        "eval() executed user-controlled code in _iterateDict; "
        "expected slice-only parse but os.getenv('USER') was called via "
        f"__import__('os').getenv('USER') expression. Calls: {getenv_calls}"
    )
