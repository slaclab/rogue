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
#ifndef ROGUE_GILRELEASE_H
#define ROGUE_GILRELEASE_H
#include "rogue/Directives.h"

#ifndef NO_PYTHON
    #include <boost/python.hpp>
#endif

namespace rogue {

//! Logging
class GilRelease {
#ifndef NO_PYTHON
    PyThreadState* state_;
#endif

  public:
    GilRelease();
    ~GilRelease();
    void acquire();
    void release();
};
}  // namespace rogue

#endif
