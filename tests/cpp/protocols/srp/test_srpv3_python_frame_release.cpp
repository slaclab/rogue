/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression test for SrpV3Emulation releasing a Python-owned frame from its
 * worker thread.
 *
 * acceptFrame() queues the caller's frame rather than a copy, so a frame
 * allocated from Python via Master._reqFrame() reaches runThread() still
 * carrying the Boost.Python shared_ptr_deleter that owns the PyObject. That
 * deleter calls Py_DECREF without acquiring the GIL, so releasing the last
 * reference on the worker thread (which holds no PyThreadState) aborts the
 * interpreter with "PyThreadState_Get: the function must be called with the GIL
 * held". Same defect as the Fifo noCopy path.
 *
 * Isolated in its own binary: on an unpatched build the fault is a fatal
 * interpreter abort, so keeping it separate means a regression here cannot take
 * down the other protocol cpp cases.
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

#define NO_IMPORT_ARRAY
#include "doctest/doctest.h"
#include "rogue/numpy.h"
#include "support/test_python.h"

// Driven from embedded Python so the queued FramePtr carries a real
// Boost.Python deleter. A frame built in C++ never does, and the test would
// pass against a broken library.
TEST_CASE("SrpV3Emulation releases Python-owned frames under the GIL") {
    try {
        REQUIRE_EQ(rogue_test_initialize_python_numpy(), 0);

        namespace bp = boost::python;
        bp::object main    = bp::import("__main__");
        bp::object globals = main.attr("__dict__");

        const char* reproducer = R"PY(
import time
import rogue.interfaces.stream as ris
import rogue.protocols.srp as srp

src  = ris.Master()
emu  = srp.SrpV3Emulation()
sink = ris.Slave()
src >> emu >> sink

for _ in range(8):
    frame = src._reqFrame(64, True)
    frame.write(bytearray(64), 0)
    src._sendFrame(frame)

    # Drop the Python-side reference so the worker owns the last one, then let
    # it run: that is what turns the release into a Py_DECREF on a thread with
    # no PyThreadState.
    del frame
    time.sleep(0.01)

time.sleep(0.2)
sentinel = True
)PY";

        bp::exec(reproducer, globals, globals);

        // Reaching here at all means no GIL-less Py_DECREF occurred: an unpatched
        // library aborts the process inside _sendFrame.
        CHECK(bp::extract<bool>(globals["sentinel"])());
    } catch (const boost::python::error_already_set&) {
        if (PyErr_Occurred()) {
            PyErr_Print();
            PyErr_Clear();
        }
        FAIL("Python exception occurred while exercising SrpV3Emulation frame release");
    }
}
