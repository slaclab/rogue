/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression test for a ZmqClient subscriber thread delivering an update to
 * a Python subclass after the interpreter has been finalized.
 *
 * Isolated in its own binary: the test finalizes the embedded interpreter,
 * and on an unpatched build the late update faults inside PyGILState_Ensure.
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
#include <unistd.h>
#include <zmq.h>

#include <boost/python.hpp>
#include <chrono>
#include <memory>
#include <string>
#include <thread>

#include "doctest/doctest.h"
#include "rogue/GilRelease.h"
#include "rogue/ScopedGil.h"
#include "rogue/interfaces/ZmqClient.h"
#include "support/test_helpers.h"
#include "support/test_python.h"

namespace {

// Binds pub on the first free port of a pid-derived range; returns the port or 0.
uint16_t bindPublisher(void* pub) {
    const uint16_t start = static_cast<uint16_t>(20000 + ((getpid() % 200) * 128));

    for (uint32_t offset = 0; offset < 128; offset += 4) {
        const uint16_t port = static_cast<uint16_t>(start + offset);
        const std::string ep = "tcp://127.0.0.1:" + std::to_string(port);
        if (zmq_bind(pub, ep.c_str()) == 0) return port;
    }
    return 0;
}

}  // namespace

// A Python application that never stops its client leaves the subscriber
// thread running while the interpreter shuts down, and an update arriving
// then used to take the GIL on a finalized interpreter.
TEST_CASE("ZmqClient does not call a Python subclass after the interpreter is finalized") {
    REQUIRE_EQ(rogue_test_initialize_python_numpy(), 0);

    namespace bp = boost::python;

    void* ctx = zmq_ctx_new();
    void* pub = zmq_socket(ctx, ZMQ_PUB);
    REQUIRE(pub != nullptr);
    const uint16_t port = bindPublisher(pub);
    REQUIRE_MESSAGE(port != 0, "Could not bind a ZMQ PUB socket on an available port");

    // Holds the Python client through a Boost.Python deleter that calls
    // Py_DECREF, which must never run after finalization, so it is
    // deliberately leaked for the rest of the process.
    std::shared_ptr<rogue::interfaces::ZmqClient>* client = nullptr;

    bool reachedPython = false;
    try {
        bp::object main    = bp::import("__main__");
        bp::object globals = main.attr("__dict__");
        globals["PORT"]    = port;

        const char* source = R"PY(
import rogue.interfaces


class Client(rogue.interfaces.ZmqClient):
    def __init__(self, port):
        super().__init__('127.0.0.1', port, False)
        self.calls = 0

    def _doUpdate(self, data):
        self.calls += 1


client = Client(PORT)
)PY";
        bp::exec(source, globals, globals);
        rogue::interfaces::ZmqClientWrapPtr wrap = bp::extract<rogue::interfaces::ZmqClientWrapPtr>(globals["client"]);
        client = new std::shared_ptr<rogue::interfaces::ZmqClient>(wrap);

        // While Python is alive an update reaches the Python override. PUB/SUB
        // drops messages until the subscription is in place, so keep sending.
        bp::object pyClient = globals["client"];
        {
            rogue::GilRelease noGil;
            reachedPython = rogue_test::waitUntil(
                [&]() {
                    zmq_send(pub, "ping", 4, ZMQ_DONTWAIT);
                    rogue::ScopedGil gil;
                    return bp::extract<int>(pyClient.attr("calls"))() >= 1;
                },
                2000);
        }
    } catch (const bp::error_already_set&) {
        if (PyErr_Occurred()) {
            PyErr_Print();
            PyErr_Clear();
        }
        FAIL("Python exception occurred while building the Python ZmqClient");
    }

    REQUIRE(reachedPython);

    Py_FinalizeEx();

    // Updates delivered now must be dropped rather than take the GIL on the
    // finalized interpreter.
    for (int i = 0; i < 20; i++) {
        zmq_send(pub, "ping", 4, ZMQ_DONTWAIT);
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }

    (*client)->stop();
    CHECK(true);

    zmq_close(pub);
    zmq_ctx_term(ctx);
}
