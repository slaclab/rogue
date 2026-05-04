#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Audit repro for PYR-006.
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


def test_zmqserver_pickle_loads_unsafe_pyr_006():
    """PYR-006: ZmqServer._doRequest uses raw pickle.loads on network bytes."""
    import pyrogue.interfaces._ZmqServer as zmq_mod

    src = inspect.getsource(zmq_mod)

    # The unsafe pattern: bare pickle.loads() call inside _doRequest.
    # A safe implementation would use a restricted unpickler or JSON.
    assert "pickle.loads" not in src, (
        "PYR-006: ZmqServer._doRequest uses raw pickle.loads on "
        "attacker-controllable bytes (line 90); arbitrary code execution "
        "is possible if the ZMQ REP port is reachable by an adversary"
    )
