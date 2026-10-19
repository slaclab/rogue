/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression test for ZmqServer worker threads serving a request through a
 * Python subclass after the interpreter has been finalized.
 *
 * Isolated in its own binary: the test finalizes the embedded interpreter,
 * and on an unpatched build the next request faults inside PyGILState_Ensure.
 * ----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to
 * the license terms in the LICENSE.txt file found in the top-level directory
 * of this distribution and at:
 *    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
 * No part of the rogue software platform, including this file, may be
 * copied, modified, propagated, or distributed except according to the terms
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
 **/
#include "rogue/Directives.h"

#include <stdint.h>
#include <zmq.h>

#include <boost/python.hpp>
#include <memory>
#include <string>

#include "doctest/doctest.h"
#include "rogue/GilRelease.h"
#include "rogue/ScopedGil.h"
#include "rogue/interfaces/ZmqServer.h"
#include "support/test_python.h"

namespace {

struct Reply {
    bool received;
    std::string data;
};

// Sends payload to a REP socket on port over a fresh REQ socket and waits up
// to two seconds for the answer.
Reply roundTrip(void* ctx, uint16_t port, const std::string& payload) {
    Reply ret{false, ""};
    void* req = zmq_socket(ctx, ZMQ_REQ);
    if (req == nullptr) return ret;

    int32_t opt = 2000;
    zmq_setsockopt(req, ZMQ_RCVTIMEO, &opt, sizeof(opt));
    opt = 0;
    zmq_setsockopt(req, ZMQ_LINGER, &opt, sizeof(opt));

    const std::string ep = "tcp://127.0.0.1:" + std::to_string(port);
    if (zmq_connect(req, ep.c_str()) == 0 && zmq_send(req, payload.data(), payload.size(), 0) >= 0) {
        zmq_msg_t msg;
        zmq_msg_init(&msg);
        const int n = zmq_msg_recv(&msg, req, 0);
        if (n >= 0) {
            ret.received = true;
            ret.data.assign(reinterpret_cast<const char*>(zmq_msg_data(&msg)), static_cast<size_t>(n));
        }
        zmq_msg_close(&msg);
    }
    zmq_close(req);
    return ret;
}

}  // namespace

// A Python application that exits without Root.stop() leaves the server
// threads running while the interpreter shuts down, and a request arriving
// then used to take the GIL on a finalized interpreter.
TEST_CASE("ZmqServer does not call a Python subclass after the interpreter is finalized") {
    REQUIRE_EQ(rogue_test_initialize_python_numpy(), 0);

    namespace bp = boost::python;

    void* ctx = zmq_ctx_new();

    // Holds the Python server through a Boost.Python deleter that calls
    // Py_DECREF, which must never run after finalization, so it is
    // deliberately leaked for the rest of the process.
    std::shared_ptr<rogue::interfaces::ZmqServer>* server = nullptr;
    uint16_t port = 0;

    int requests = 0;
    int strings  = 0;
    try {
        bp::object main    = bp::import("__main__");
        bp::object globals = main.attr("__dict__");

        const char* source = R"PY(
import rogue.interfaces


class Server(rogue.interfaces.ZmqServer):
    def __init__(self):
        super().__init__('127.0.0.1', 0)
        self.requests = 0
        self.strings = 0

    def _doRequest(self, data):
        self.requests += 1
        return b'ok'

    def _doString(self, data):
        self.strings += 1
        return 'ok'


server = Server()
server._start()
)PY";
        bp::exec(source, globals, globals);
        rogue::interfaces::ZmqServerWrapPtr wrap = bp::extract<rogue::interfaces::ZmqServerWrapPtr>(globals["server"]);
        server = new std::shared_ptr<rogue::interfaces::ZmqServer>(wrap);
        port = (*server)->port();

        // While Python is alive both request paths reach the Python overrides.
        Reply binary;
        Reply text;
        {
            rogue::GilRelease noGil;
            binary = roundTrip(ctx, port + 1, "req");
            text   = roundTrip(ctx, port + 2, "str");
        }
        CHECK(binary.received);
        CHECK_EQ(binary.data, "ok");
        CHECK(text.received);
        CHECK_EQ(text.data, "ok");

        bp::object pyServer = globals["server"];
        requests            = bp::extract<int>(pyServer.attr("requests"));
        strings             = bp::extract<int>(pyServer.attr("strings"));
    } catch (const bp::error_already_set&) {
        if (PyErr_Occurred()) {
            PyErr_Print();
            PyErr_Clear();
        }
        FAIL("Python exception occurred while building the Python ZmqServer");
    }

    REQUIRE_EQ(requests, 1);
    REQUIRE_EQ(strings, 1);

    Py_FinalizeEx();

    // Requests served now must get the empty default reply rather than take
    // the GIL on the finalized interpreter. The empty reply keeps the REP
    // sockets out of the EFSM state for later requests.
    const Reply binary = roundTrip(ctx, port + 1, "req");
    CHECK(binary.received);
    CHECK_EQ(binary.data, "");

    const Reply text = roundTrip(ctx, port + 2, "str");
    CHECK(text.received);
    CHECK_EQ(text.data, "");

    (*server)->stop();

    zmq_ctx_term(ctx);
}
