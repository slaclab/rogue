#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Regression test for the ZmqServer pickle-payload audit fix.
#
#   Pre-fix, ``ZmqServer._doRequest`` deserialised attacker-controllable
#   network bytes with raw ``pickle.loads(data)``, which the pickle docs
#   explicitly call out as unsafe (the REDUCE opcode can invoke any callable
#   reachable by name).  The fix funnels every binary request through the
#   restricted ``_safe_loads()`` helper backed by ``_SafeUnpickler``.
#
#   This source-text test pins three structural invariants on ``_doRequest``:
#
#     * No reference (call, alias, RHS expression) to any raw pickle entry
#       point that can deserialise attacker bytes -- ``pickle.loads`` /
#       ``_pickle.loads`` (the original bug), ``pickle.load`` /
#       ``_pickle.load`` (file-object variant), or ``pickle.Unpickler`` /
#       ``_pickle.Unpickler`` (constructor; ``Unpickler(...).load()`` is
#       equally unsafe and aliased forms must be caught too).
#
#     * ``_safe_loads`` is actually called -- a regression that swaps the
#       choke point for some other helper would lose this invariant.
#
#     * ``_safe_loads`` is called with the bytes parameter (``data``) as an
#       argument.  Without this third pin a regression could keep a no-op
#       ``_safe_loads(b'')`` somewhere in the body for show while routing
#       the real request bytes through a raw pickle entry point.
#
#   The walks are scoped to the AST of just ``_doRequest`` via
#   ``inspect.getsource``, so unrelated comments, docstrings, or helpers
#   elsewhere in the module cannot satisfy or trip the assertions.
#   Behavioural coverage of the allowlist itself lives in
#   ``tests/interfaces/test_zmq_safe_unpickler_behavior.py``.
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import ast
import inspect
import textwrap


def _calls_in(tree):
    """Yield every ast.Call node reachable from ``tree``."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            yield node


def _called_names(tree):
    """Return the set of function-call names (final attr/Name) in ``tree``."""
    names = set()
    for call in _calls_in(tree):
        func = call.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def _references_to(tree, qualified_names):
    """Return the subset of ``qualified_names`` that appear as Attribute nodes in ``tree``."""
    wanted = set(qualified_names)
    seen = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            qn = f"{node.value.id}.{node.attr}"
            if qn in wanted:
                seen.add(qn)
    return seen


def _safe_loads_called_with(tree, arg_name):
    """Return True iff a ``_safe_loads(...)`` call in ``tree`` receives ``arg_name``."""
    for call in _calls_in(tree):
        func = call.func
        terminal = None
        if isinstance(func, ast.Name):
            terminal = func.id
        elif isinstance(func, ast.Attribute):
            terminal = func.attr
        if terminal != "_safe_loads":
            continue
        for arg in call.args:
            for sub in ast.walk(arg):
                if isinstance(sub, ast.Name) and sub.id == arg_name:
                    return True
    return False


def test_zmqserver_do_request_uses_safe_unpickler():
    """ZmqServer._doRequest must funnel network bytes through _safe_loads()."""
    from pyrogue.interfaces._ZmqServer import ZmqServer

    source = textwrap.dedent(inspect.getsource(ZmqServer._doRequest))
    tree = ast.parse(source)

    forbidden = {
        "pickle.loads",      "_pickle.loads",
        "pickle.load",       "_pickle.load",
        "pickle.Unpickler",  "_pickle.Unpickler",
    }
    unsafe_refs = _references_to(tree, forbidden)
    assert not unsafe_refs, (
        f"ZmqServer._doRequest references {sorted(unsafe_refs)} on "
        "attacker-controllable bytes; arbitrary code execution is possible "
        "if the ZMQ REP port is reachable by an adversary.  The request "
        "path must funnel through the restricted _safe_loads() helper (or "
        "json.loads for the string-payload codepath).  Aliasing the raw "
        "callable (``loads = _pickle.loads``) is also forbidden."
    )

    assert "_safe_loads" in _called_names(tree), (
        "ZmqServer._doRequest must deserialise the incoming payload via a "
        "_safe_loads() call; the restricted Unpickler is the choke point "
        "that blocks the REDUCE-opcode arbitrary-callable path."
    )

    assert _safe_loads_called_with(tree, "data"), (
        "ZmqServer._doRequest must pass the incoming ``data`` parameter to "
        "_safe_loads(); a no-op _safe_loads(b'') call on a sibling expression "
        "would satisfy the substring/Call-name checks but leave the request "
        "bytes routed through some other (presumed unsafe) deserialiser."
    )
