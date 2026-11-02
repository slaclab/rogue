/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression test for a C++ memory Master delivering a transaction to a
 * Python Slave or Hub after the interpreter has been finalized.
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
#include <string>

#define NO_IMPORT_ARRAY
#include "doctest/doctest.h"
#include "rogue/interfaces/memory/Constants.h"
#include "rogue/interfaces/memory/Hub.h"
#include "rogue/interfaces/memory/Master.h"
#include "rogue/interfaces/memory/Slave.h"
#include "rogue/numpy.h"
#include "support/test_python.h"

namespace rim = rogue::interfaces::memory;

namespace {

// Issues one four byte read through master and returns the resulting error
// string, empty on success.
std::string readOnce(rim::Master& master) {
    uint8_t data[4] = {0, 0, 0, 0};
    master.clearError();
    uint32_t id = master.reqTransaction(0, sizeof(data), data, rim::Read);
    master.waitTransaction(id);
    return master.getError();
}

}  // namespace

// A Python application whose hardware threads (TcpServer, SRP, RSSI, AXI DMA)
// outlive Root.stop() can still deliver a transaction to a Python memory Slave
// while the interpreter shuts down, and that delivery used to take the GIL on
// a finalized interpreter.
TEST_CASE("Memory Master does not call a Python Slave or Hub after the interpreter is finalized") {
    REQUIRE_EQ(rogue_test_initialize_python_numpy(), 0);

    namespace bp = boost::python;

    // Every owner below holds a Python object through a Boost.Python deleter
    // that calls Py_DECREF, which must never run after finalization, so they
    // are deliberately leaked for the rest of the process.
    rim::SlavePtr* slave        = nullptr;
    rim::HubPtr* hub            = nullptr;
    rim::MasterPtr* slaveMaster = new rim::MasterPtr(rim::Master::create());
    rim::MasterPtr* hubMaster   = new rim::MasterPtr(rim::Master::create());

    (*slaveMaster)->setTimeout(1000000);
    (*hubMaster)->setTimeout(1000000);

    int slaveCalls = 0;
    int hubCalls   = 0;
    try {
        bp::object main    = bp::import("__main__");
        bp::object globals = main.attr("__dict__");

        const char* source = R"PY(
import rogue.interfaces.memory as rim


class Slave(rim.Slave):
    def __init__(self):
        super().__init__(4, 4)
        self.calls = 0

    def _doMinAccess(self):
        return 1

    def _doMaxAccess(self):
        return 1

    def _doAddress(self):
        return 1

    def _doTransaction(self, transaction):
        self.calls += 1
        transaction.done()


class Hub(rim.Hub):
    def __init__(self):
        super().__init__(0, 4, 4)
        self.calls = 0

    def _doTransaction(self, transaction):
        self.calls += 1
        transaction.done()


slave = Slave()
hub = Hub()
)PY";
        bp::exec(source, globals, globals);
        slave = new rim::SlavePtr(bp::extract<rim::SlavePtr>(globals["slave"]));
        rim::HubWrapPtr hubWrap = bp::extract<rim::HubWrapPtr>(globals["hub"]);
        hub                     = new rim::HubPtr(hubWrap);

        // The Hub forwards to a plain C++ Slave once its Python override is
        // skipped, so the fall through below reports the unconnected bus.
        (*hub)->setSlave(rim::Slave::create(4, 4));
        (*slaveMaster)->setSlave(*slave);
        (*hubMaster)->setSlave(*hub);

        // While Python is alive every wrapper reaches its Python override.
        CHECK_EQ((*slave)->doMinAccess(), 1U);
        CHECK_EQ((*slave)->doMaxAccess(), 1U);
        CHECK_EQ((*slave)->doAddress(), 1U);
        CHECK_EQ(readOnce(**slaveMaster), "");
        CHECK_EQ(readOnce(**hubMaster), "");

        slaveCalls = bp::extract<int>(globals["slave"].attr("calls"));
        hubCalls   = bp::extract<int>(globals["hub"].attr("calls"));
    } catch (const bp::error_already_set&) {
        if (PyErr_Occurred()) {
            PyErr_Print();
            PyErr_Clear();
        }
        FAIL("Python exception occurred while building the Master to Python Slave paths");
    }

    REQUIRE_EQ(slaveCalls, 1);
    REQUIRE_EQ(hubCalls, 1);

    Py_FinalizeEx();

    // Calls made now must fall back to the C++ base methods rather than take
    // the GIL on the finalized interpreter.
    CHECK_EQ((*slave)->doMinAccess(), 4U);
    CHECK_EQ((*slave)->doMaxAccess(), 4U);
    CHECK_EQ((*slave)->doAddress(), 0U);
    CHECK_EQ(readOnce(**slaveMaster), "Unsupported transaction using unconnected memory bus");
    CHECK_EQ(readOnce(**hubMaster), "Unsupported transaction using unconnected memory bus");
}
