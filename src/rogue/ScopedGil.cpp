/**
 *-----------------------------------------------------------------------------
 * Title      : Scoped GIL
 * ----------------------------------------------------------------------------
 * File       : ScopedGil.h
 * Created    : 2017-06-08
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
#include <rogue/ScopedGil.h>

rogue::ScopedGil::ScopedGil() {
#ifndef NO_PYTHON
   state_ = PyGILState_Ensure();
#endif
}

rogue::ScopedGil::~ScopedGil() {
#ifndef NO_PYTHON
   PyGILState_Release(state_);
#endif
}

