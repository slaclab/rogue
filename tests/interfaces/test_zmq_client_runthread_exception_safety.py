#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : ZmqClient runThread exception-safety regression
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
# Pin the contract that ``ZmqClient::runThread()`` cannot let an exception
# escape the worker function and std::terminate() the process.
#
# The pre-fix runThread had two bare exit points between ``zmq_recvmsg()``
# and the next ``zmq_msg_close()``:
#   * ``Py_BuildValue("y#", ...) == NULL`` (extremely rare in practice)
#   * Any uncaught exception out of ``this->doUpdate(dat)``. The wrapper
#     ``ZmqClientWrap::doUpdate`` catches Python-side throws via
#     ``catch (...) { PyErr_Print(); }``, but a misbehaving boost::python
#     binding (e.g. an ``__del__`` on the bytes wrapper raising during
#     stack unwind, or ``bp::override`` lookup on a half-finalized
#     interpreter) can still reach the worker. The fix wraps the entire
#     Python-touching path in try/catch so the worker drops the bad frame
#     and continues serving.
#
# This test mirrors ``test_zmq_server_runthread_exception_safety.py`` for
# the publish/subscribe path. It exercises the worker by registering a
# ``_doUpdate`` override that always raises a Python exception. With the
# wrapper's ``PyErr_Print`` + the new runThread try/catch in place, the
# SUB worker stays alive and processes successive publishes; without the
# layered protection, the first bad frame brings down the worker (or, in
# the worst case, std::terminate()s the process).

import time

import rogue.interfaces


class _RaisingClient(rogue.interfaces.ZmqClient):
    """ZmqClient override whose ``_doUpdate`` always raises.

    Counter is incremented BEFORE raising so the test can verify the SUB
    worker re-entered the loop after the previous throw.
    """

    def __init__(self, addr: str, port: int) -> None:
        rogue.interfaces.ZmqClient.__init__(self, addr, port, False)
        self.update_count = 0

    def _doUpdate(self, data):  # noqa: D401 - boost.python override
        self.update_count += 1
        raise RuntimeError("intentional _doUpdate failure")


def test_zmq_client_runthread_survives_raising_doUpdate(free_zmq_port):
    """Repeated raising ``_doUpdate`` callbacks must not kill the SUB worker.

    Reverting either the wrapper's ``PyErr_Print`` catch in
    ``ZmqClientWrap::doUpdate`` or the new try/catch in
    ``ZmqClient::runThread`` lets the first raised exception escape the
    std::thread function and the C++ runtime terminates the process.
    With the layered protection the worker logs and drops the bad frame,
    so ``update_count`` keeps climbing across successive publishes.
    """
    port = free_zmq_port

    server = rogue.interfaces.ZmqServer("127.0.0.1", port)
    server._start()

    try:
        client = _RaisingClient("127.0.0.1", port)

        try:
            # ZMQ PUB/SUB connect is asynchronous: the SUB socket needs a
            # short moment to subscribe before the publisher's frames are
            # delivered. Loop on small publishes until the first one lands,
            # then push enough additional frames to prove the worker
            # survived the first raise and processed several more.
            target_count = 5
            deadline = time.monotonic() + 10.0
            payload = b"runthread-exception-safety-probe"

            while client.update_count < target_count and time.monotonic() < deadline:
                server._publish(payload)
                time.sleep(0.05)

            assert client.update_count >= target_count, (
                f"ZmqClient SUB worker stopped processing after"
                f" {client.update_count} update(s); the runThread try/catch"
                f" or the wrapper's PyErr_Print catch is not protecting"
                f" against raising _doUpdate overrides"
            )
        finally:
            client._stop()
    finally:
        server._stop()
