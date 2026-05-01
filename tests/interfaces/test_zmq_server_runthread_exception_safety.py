#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : ZmqServer runThread exception-safety regression
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
# Pin the contract that ``ZmqServer::runThread()`` cannot let an exception
# escape the worker function and std::terminate() the process.
#
# The pre-fix runThread had two raw ``throw`` sites between
# ``zmq_recvmsg()`` and the next ``zmq_msg_close()``:
#   * ``Py_BuildValue("y#", ...) == NULL`` (extremely rare in practice)
#   * ``PyObject_GetBuffer(ret.ptr(), ...)`` < 0 — fires whenever a Python
#     ``_doRequest`` override returns an object that does not expose a
#     readable buffer (e.g. ``None``, an ``int``, a list).
#
# Either ``throw`` propagates out of the std::thread function. The C++
# runtime then calls ``std::terminate()`` because no thread function may
# let an exception escape. The fix wraps the Python-touching path in a
# try/catch so the worker drops the bad request and continues serving.
#
# The test below exercises the second path by overriding ``_doRequest``
# on a ``rogue.interfaces.ZmqServer`` to return ``None`` (no buffer
# protocol). It then confirms:
#   1. The process is not terminated by the bad request.
#   2. The server thread is still alive — ``_stop()`` returns cleanly,
#      which only happens when ``runThread`` is still in its loop and
#      observing ``threadEn_``.
#
# Reverting the try/catch in ZmqServer.cpp::runThread makes step 2 race
# the std::terminate(); ``_stop()`` never returns and the test process
# is killed.

import pickle
import time

import rogue.interfaces


class _BadResponseServer(rogue.interfaces.ZmqServer):
    """ZmqServer override whose ``_doRequest`` returns a non-buffer object."""

    def __init__(self, addr: str, port: int) -> None:
        rogue.interfaces.ZmqServer.__init__(self, addr, port)
        self.requestCount = 0

    def _doRequest(self, data):  # noqa: D401 - boost.python override
        # ``None`` does not expose the Python buffer protocol; the C++
        # runThread must catch the resulting GeneralError and continue.
        self.requestCount += 1
        return None


def test_zmq_server_runthread_survives_bad_response(free_zmq_port):
    """A ``_doRequest`` returning ``None`` must not std::terminate() the process.

    Reverting the try/catch in ZmqServer.cpp::runThread makes the rogue
    runtime kill the test process when the first request lands. With the
    fix, ``_stop()`` returns cleanly and the server is still serving.
    """
    port = free_zmq_port

    server = _BadResponseServer("127.0.0.1", port)
    try:
        server._start()

        # Build a binary client and send one request. The server thread
        # will invoke ``_doRequest`` (returning None), the C++ side will
        # try to extract a buffer, throw GeneralError, and (with the fix)
        # log + drop the request. Without the fix the worker thread
        # uncaught-throws and the runtime calls std::terminate().
        client = rogue.interfaces.ZmqClient("127.0.0.1", port, False)
        try:
            # Use a short timeout so this test cannot hang the suite if
            # the request silently drops; one round-trip is enough.
            client.setTimeout(500, False)

            # Retry a few times because ZMQ REQ-REP connect is
            # asynchronous and the first send may race the server's
            # bind() completion.
            # ZmqClient._send takes a pickled dict on the binary path; the
            # payload contents do not matter — the server's _doRequest
            # ignores them and returns None to trigger the runThread throw.
            payload = pickle.dumps({"attr": "noop", "path": ""})
            deadline = time.monotonic() + 5.0
            while server.requestCount == 0 and time.monotonic() < deadline:
                try:
                    client._send(payload)
                except Exception:
                    # Expected: no valid response was produced. We only
                    # care that the server thread did not bring down
                    # the process.
                    pass
                time.sleep(0.1)

            assert server.requestCount >= 1, (
                "ZmqServer never invoked _doRequest; cannot exercise the"
                " runThread exception path"
            )

            # If the worker had terminated, _stop() below would deadlock
            # on thread.join(). Reaching the assertion above already
            # proves runThread looped back after the throw.
        finally:
            client._stop()
    finally:
        server._stop()
