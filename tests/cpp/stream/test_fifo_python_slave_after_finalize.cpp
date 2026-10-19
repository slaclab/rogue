/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression test for a stream FIFO worker delivering a frame to a Python
 * Slave after the interpreter has been finalized.
 *
 * Isolated in its own binary: the test finalizes the embedded interpreter,
 * and on an unpatched build the late delivery faults inside
 * PyGILState_Ensure.
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

#include <boost/python.hpp>
#include <memory>

#define NO_IMPORT_ARRAY
#include "doctest/doctest.h"
#include "rogue/GilRelease.h"
#include "rogue/ScopedGil.h"
#include "rogue/interfaces/stream/Fifo.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/numpy.h"
#include "support/test_helpers.h"
#include "support/test_python.h"

namespace ris = rogue::interfaces::stream;

// A Python application that never stops its producers leaves FIFO workers
// running while the interpreter shuts down, and a frame arriving then used to
// take the GIL on a finalized interpreter.
TEST_CASE("Stream FIFO does not call a Python Slave after the interpreter is finalized") {
    REQUIRE_EQ(rogue_test_initialize_python_numpy(), 0);

    namespace bp = boost::python;
    auto pool = rogue_test::makePool();

    // Both owners hold the Python Sink through a Boost.Python deleter that
    // calls Py_DECREF, which must never run after finalization, so they are
    // deliberately leaked for the rest of the process.
    ris::SlavePtr* sink = nullptr;
    ris::FifoPtr* fifo  = new ris::FifoPtr(ris::Fifo::create(0, 0, false));

    bool reachedPython = false;
    try {
        bp::object main    = bp::import("__main__");
        bp::object globals = main.attr("__dict__");

        const char* source = R"PY(
import rogue.interfaces.stream as ris


class Sink(ris.Slave):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def _acceptFrame(self, frame):
        self.calls += 1


sink = Sink()
)PY";
        bp::exec(source, globals, globals);
        sink = new ris::SlavePtr(bp::extract<ris::SlavePtr>(globals["sink"]));
        (*fifo)->addSlave(*sink);

        // While Python is alive the frame reaches the Python override.
        (*fifo)->acceptFrame(rogue_test::makeFrame(pool, {0x01, 0x02, 0x03, 0x04}));
        bp::object pySink = globals["sink"];
        {
            rogue::GilRelease noGil;
            reachedPython = rogue_test::waitUntil(
                [&]() {
                    rogue::ScopedGil gil;
                    return bp::extract<int>(pySink.attr("calls"))() == 1;
                },
                2000);
        }
    } catch (const bp::error_already_set&) {
        if (PyErr_Occurred()) {
            PyErr_Print();
            PyErr_Clear();
        }
        FAIL("Python exception occurred while building the FIFO to Python Sink path");
    }

    REQUIRE(reachedPython);

    // The Python override returns without calling the C++ base Slave, so its
    // counter is still zero here.
    CHECK_EQ((*sink)->getFrameCount(), 0U);

    Py_FinalizeEx();

    // A frame delivered now must fall back to the C++ base Slave rather than
    // take the GIL on the finalized interpreter.
    (*fifo)->acceptFrame(rogue_test::makeFrame(pool, {0x05, 0x06, 0x07, 0x08}));
    CHECK(rogue_test::waitUntil([&]() { return (*sink)->getFrameCount() == 1U; }, 2000));
}
