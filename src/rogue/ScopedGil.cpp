/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Acquire the GIL for the scope of this class.
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
#include "rogue/ScopedGil.h"

#include "rogue/PerfCounters.h"

// The constructor and destructor bodies are Python-build-only: they compile
// only when NO_PYTHON is undefined, so a C++ doctest with no Python
// interpreter can never call either one. Behavioural coverage for this
// counter family is the Python-level test in
// tests/utilities/test_perf_counters.py instead.
//
// Both crossings below are unconditional, so one ScopedGil scope contributes
// exactly two to gScopedGilCount, not one: this counts crossings, not scopes.
rogue::ScopedGil::ScopedGil() {
#ifndef NO_PYTHON
    state_ = PyGILState_Ensure();
    rogue::perf::gScopedGilCount.fetch_add(1, std::memory_order_relaxed);
#endif
}

rogue::ScopedGil::~ScopedGil() {
#ifndef NO_PYTHON
    PyGILState_Release(state_);
    rogue::perf::gScopedGilCount.fetch_add(1, std::memory_order_relaxed);
#endif
}
