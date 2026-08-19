/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Release GIL for the scope of this class.
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

#include "rogue/GilRelease.h"

#include <stdint.h>

#include "rogue/PerfCounters.h"

#ifndef NO_PYTHON
    #include <boost/python.hpp>
namespace bp = boost::python;
#endif

rogue::GilRelease::GilRelease() {
#ifndef NO_PYTHON
    state_ = NULL;
    release();
#endif
}

rogue::GilRelease::~GilRelease() {
#ifndef NO_PYTHON
    acquire();
#endif
}

// Both acquire() and release() are Python-build-only: their entire bodies
// compile only when NO_PYTHON is undefined, so a C++ doctest with no Python
// interpreter can never observe a real crossing here. Behavioural coverage
// for this counter family is the Python-level test in
// tests/utilities/test_perf_counters.py instead.
void rogue::GilRelease::acquire() {
#ifndef NO_PYTHON
    if (state_ != NULL) {
        PyEval_RestoreThread(state_);
        // The crossing is this branch, not the call: only a state_ that was
        // actually saved by release() gets restored here.
        rogue::perf::gGilAcquireCount.fetch_add(1, std::memory_order_relaxed);
    }
    state_ = NULL;
#endif
}

void rogue::GilRelease::release() {
#ifndef NO_PYTHON
    if (Py_IsInitialized() && PyGILState_Check()) {
        state_ = PyEval_SaveThread();
        // The crossing is this branch, not the call: counting at function
        // entry would scale with call count rather than with crossings.
        rogue::perf::gGilReleaseCount.fetch_add(1, std::memory_order_relaxed);
    } else {
        state_ = NULL;
    }
#endif
}
