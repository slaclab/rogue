#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""BaseVariable._setDict eval injection repro.

`BaseVariable._setDict` in python/pyrogue/_Variable.py formerly called
eval(f'[i for i in range(self._numValues())][{keys[0]}]') where keys[0]
is derived from caller-supplied YAML keys. A key containing arbitrary Python
code would execute it. This test verifies the fix rejects such payloads via
AST-based slice parsing without executing arbitrary code.
"""

import os

import pyrogue as pr
import rogue.interfaces.memory as rim


class ArrayDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add(pr.RemoteVariable(
            name='ArrVar',
            offset=0x0,
            bitSize=8,
            base=pr.UInt,
            mode='RW',
            numValues=4,
            valueBits=8,
            valueStride=8,
        ))


class SetDictEvalRoot(pr.Root):
    def __init__(self):
        super().__init__(name='root', pollEn=False)
        self._mem = rim.Emulate(4, 0x100)
        self.addInterface(self._mem)
        self.add(ArrayDevice(name='Dev', memBase=self._mem))


def test_variable_setdict_eval_injection(monkeypatch):
    """Verify that _setDict rejects eval-injectable slice keys."""
    original_getenv = os.getenv
    getenv_calls = []

    def tracking_getenv(key, *args, **kwargs):
        getenv_calls.append(key)
        return original_getenv(key, *args, **kwargs)

    monkeypatch.setattr(os, 'getenv', tracking_getenv)

    with SetDictEvalRoot() as root:
        var = root.Dev.ArrVar
        payload = "__import__('os').getenv('USER')"
        try:
            var._setDict(1, writeEach=False, modes=['RW'], keys=[payload])
        except Exception:
            pass  # VariableError expected; we only care whether side-effect fired

    assert 'USER' not in getenv_calls, (
        "eval() executed user-controlled code in BaseVariable._setDict; "
        "expected slice-only parse but os.getenv('USER') was called via "
        f"__import__('os').getenv('USER') expression. Calls: {getenv_calls}"
    )
