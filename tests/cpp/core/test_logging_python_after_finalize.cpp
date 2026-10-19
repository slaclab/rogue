/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression test for rogue::Logging forwarding a C++ log record into Python
 * logging after the interpreter has been finalized.
 *
 * Isolated in its own binary: the test finalizes the embedded interpreter,
 * and on an unpatched build the late record faults inside PyGILState_Ensure.
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

#include <boost/python.hpp>
#include <memory>
#include <thread>

#include "doctest/doctest.h"
#include "rogue/Logging.h"
#include "support/test_python.h"

// With unified logging enabled every C++ log record is handed to Python
// logging under the GIL. Worker threads keep logging while a Python
// application shuts down, and a record emitted then used to take the GIL on
// a finalized interpreter.
TEST_CASE("Logging does not forward records to Python after the interpreter is finalized") {
    REQUIRE_EQ(rogue_test_initialize_python_numpy(), 0);

    namespace bp = boost::python;

    auto log = rogue::Logging::create("test.forward.finalize", true);
    rogue::Logging::setForwardPython(true);

    int received = 0;
    try {
        bp::object main    = bp::import("__main__");
        bp::object globals = main.attr("__dict__");
        globals["NAME"]    = log->name();

        const char* source = R"PY(
import logging

records = []


class Capture(logging.Handler):
    def emit(self, record):
        records.append(record.getMessage())


logger = logging.getLogger(NAME)
logger.setLevel(logging.DEBUG)
logger.addHandler(Capture())
)PY";
        bp::exec(source, globals, globals);

        // While Python is alive the record reaches the Python handler.
        log->error("before finalize");
        received = static_cast<int>(bp::len(globals["records"]));
    } catch (const bp::error_already_set&) {
        if (PyErr_Occurred()) {
            PyErr_Print();
            PyErr_Clear();
        }
        FAIL("Python exception occurred while installing the capture handler");
    }

    REQUIRE_EQ(received, 1);

    Py_FinalizeEx();

    // A record emitted now, from a worker thread as in a real teardown, must
    // skip the Python forward rather than take the GIL on the finalized
    // interpreter.
    std::thread worker([&]() { log->error("after finalize"); });
    worker.join();
    CHECK(true);

    rogue::Logging::setForwardPython(false);
}
