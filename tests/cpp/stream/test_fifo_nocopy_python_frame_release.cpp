/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression test for a FIFO built with noCopy=true releasing a Python-owned
 * frame from its worker thread.
 *
 * With noCopy=true the FIFO queues the caller's frame rather than a copy, so a
 * frame allocated from Python via Master._reqFrame() reaches the worker thread
 * still carrying the Boost.Python shared_ptr_deleter that owns the PyObject.
 * That deleter calls Py_DECREF without acquiring the GIL, so dropping the last
 * reference on the worker thread (which holds no PyThreadState) aborts the
 * interpreter with "PyThreadState_Get: the function must be called with the GIL
 * held". The first frame survives because there is no prior reference to drop;
 * the second one faults.
 *
 * Isolated in its own binary: on an unpatched build the fault is a fatal
 * interpreter abort, so keeping it separate means a regression here cannot take
 * down the other stream cpp cases.
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

// Drives the reported reproducer from embedded Python so the queued FramePtr
// carries a real Boost.Python deleter. Constructing an equivalent frame in C++
// would not attach one, and the test would pass on a broken build.
TEST_CASE("Stream FIFO with noCopy releases Python-owned frames under the GIL") {
    try {
        REQUIRE_EQ(rogue_test_initialize_python_numpy(), 0);

        namespace bp = boost::python;
        bp::object main    = bp::import("__main__");
        bp::object globals = main.attr("__dict__");

        // sentinel only flips once every frame has been pushed and the worker
        // has had the chance to release the previous one. An unpatched library
        // aborts the whole process inside _sendFrame, so reaching the check at
        // all is most of the assertion.
        const char* reproducer = R"PY(
import time
import rogue.interfaces.stream as ris

frame_count = 16

src  = ris.Master()
fifo = ris.Fifo(100, 0, True)   # noCopy=True: queues the caller's frame
sink = ris.Slave()
src >> fifo >> sink

for _ in range(frame_count):
    frame = src._reqFrame(64, True)
    frame.write(bytearray(64), 0)
    src._sendFrame(frame)

    # Drop the Python-side reference so the worker thread owns the last one,
    # then let it run. This is what turns the release into a Py_DECREF on a
    # thread with no PyThreadState.
    del frame
    time.sleep(0.01)

# Give the worker a final window to drain and release the last frame.
deadline = time.time() + 2.0
while fifo.size() > 0 and time.time() < deadline:
    time.sleep(0.01)

drained = fifo.size()
dropped = fifo.dropCnt()
sentinel = True
)PY";

        bp::exec(reproducer, globals, globals);

        // The interpreter is still alive, so no GIL-less Py_DECREF happened.
        CHECK(bp::extract<bool>(globals["sentinel"])());

        // Every frame should have moved through: none left queued, none dropped
        // (16 frames against a depth of 100, fed one at a time).
        CHECK_EQ(bp::extract<uint32_t>(globals["drained"])(), 0U);
        CHECK_EQ(bp::extract<uint32_t>(globals["dropped"])(), 0U);
    } catch (const boost::python::error_already_set&) {
        if (PyErr_Occurred()) {
            PyErr_Print();
            PyErr_Clear();
        }
        FAIL("Python exception occurred while exercising Fifo noCopy frame release");
    }
}
