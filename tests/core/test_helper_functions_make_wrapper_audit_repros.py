#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Audit repros for PYR-004 and PYR-005.
#   functionWrapper() builds a lambda source string and calls eval(ls) without
#   sanitising callArgs.  A caller who controls callArgs can inject arbitrary
#   Python code into the lambda body via a crafted string entry.
#   On HEAD both eval sites execute the injection and the sentinel env-var IS
#   read, causing the FAIL assertions below to trigger.
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import pyrogue._HelperFunctions as hf


# ---------------------------------------------------------------------------
# PYR-004 — None-function branch (line 451)
# ---------------------------------------------------------------------------
def test_function_wrapper_eval_injection_pyr_004(monkeypatch):
    """PYR-004: functionWrapper eval(ls) executes injected code via callArgs (None branch)."""
    monkeypatch.setenv("AUDIT_PYR_004_SENTINEL", "injected_004")

    # The lambda string becomes:
    #   lambda function, x: __import__('os').getenv('AUDIT_PYR_004_SENTINEL')  # : None
    # The comment discards the original ": None" body; the lambda now returns
    # the os.getenv result when called.
    injected_arg = "x: __import__('os').getenv('AUDIT_PYR_004_SENTINEL')  # "
    wrapper = hf.functionWrapper(None, [injected_arg])

    # Call the wrapper; on HEAD it executes the injection.
    outcome = wrapper(None, None)

    assert outcome != "injected_004", (
        "PYR-004: functionWrapper eval(ls) executed injected __import__/getenv "
        "code via callArgs (None-function branch, line 451); "
        "sentinel value was read"
    )


# ---------------------------------------------------------------------------
# PYR-005 — non-None function branch (line 468)
# ---------------------------------------------------------------------------
def test_function_wrapper_eval_injection_with_function_pyr_005(monkeypatch):
    """PYR-005: functionWrapper eval(ls) executes injected code via callArgs (function branch)."""
    monkeypatch.setenv("AUDIT_PYR_005_SENTINEL", "injected_005")

    def real_func():
        return "safe"

    # With a real function the lambda string becomes:
    #   lambda function, x: __import__('os').getenv('AUDIT_PYR_005_SENTINEL')  # : function()
    # Again the comment hides the intended body.
    injected_arg = "x: __import__('os').getenv('AUDIT_PYR_005_SENTINEL')  # "
    wrapper = hf.functionWrapper(real_func, [injected_arg])

    outcome = wrapper(real_func, None)

    assert outcome != "injected_005", (
        "PYR-005: functionWrapper eval(ls) executed injected __import__/getenv "
        "code via callArgs (non-None function branch, line 468); "
        "sentinel value was read"
    )
