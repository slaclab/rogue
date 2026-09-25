/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    Hardware-free SRP / RSSI burst diagnostic
 *-----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to
 * the license terms in the LICENSE.txt file found in the top-level directory
 * of this distribution and at:
 * https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
 * No part of the rogue software platform, including this file, may be
 * copied, modified, propagated, or distributed except according to the terms
 * contained in the LICENSE.txt file.
 *-----------------------------------------------------------------------------
 **/
#include "Trace.h"
#include <memory>
#include <string>
namespace burst {
Event events[capacity];
std::atomic<size_t> next{0};
std::atomic<bool> enabled{true}, armed{false};
const void* appTarget = nullptr;
const void* srpTarget = nullptr;
const void* txTarget = nullptr;
// Set before starting workers; the diagnostic exits without static teardown.
std::string mode;  // NOLINT(runtime/string)
unsigned delayMs = 200;
unsigned stallAfter = 1;
std::atomic<unsigned> stallHits{0};
bool constructingPeer = false;
}  // namespace burst
#ifndef NO_PYTHON
#include "Stack.h"
#include <boost/python.hpp>
void setupBurstPython() {
    namespace bp = boost::python;
    bp::class_<burst::Stack, std::shared_ptr<burst::Stack>, boost::noncopyable>(
        "_BurstStack", bp::init<unsigned, unsigned, unsigned, std::string>())
        .def("start", &burst::Stack::start)
        .def("open", &burst::Stack::open)
        .def("stop", &burst::Stack::stop)
        .def("memory", &burst::Stack::memory)
        .def("begin", &burst::Stack::begin)
        .def("finish", &burst::Stack::finish);
}
#endif
