#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Regression test.
#   ZmqServer._doRequest calls pickle.loads(data) on attacker-controllable
#   bytes (line 90).  The source-text test asserts this pattern is absent
#   from the file.  On HEAD it IS present, so the test FAILS.
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import inspect


def test_zmqserver_pickle_loads_unsafe():
    """ZmqServer._doRequest uses raw pickle.loads on network bytes."""
    import re

    import pyrogue.interfaces._ZmqServer as zmq_mod

    src = inspect.getsource(zmq_mod)

    # The unsafe pattern is any direct ``pickle.loads(...)`` call on
    # attacker-controllable bytes.  The module imports pickle as ``_pickle``,
    # so a future regression that introduces ``_pickle.loads(data)`` would
    # be just as unsafe and would slip past a literal ``"pickle.loads"``
    # token check.  Match either the public name or the aliased import.
    unsafe_call = re.search(r"\b_?pickle\.loads\s*\(", src)
    assert unsafe_call is None, (
        "ZmqServer._doRequest uses a raw pickle.loads() (or _pickle.loads()) "
        "on attacker-controllable bytes; arbitrary code execution is "
        "possible if the ZMQ REP port is reachable by an adversary.  The "
        "request path must funnel through the restricted _safe_loads() "
        "helper (or json.loads for the string-payload codepath)."
    )
