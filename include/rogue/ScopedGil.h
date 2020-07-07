/**
 *-----------------------------------------------------------------------------
 * Title      : Scoped GIL
 * ----------------------------------------------------------------------------
 * File       : ScopedGil.h
 * Created    : 2017-02-28
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
#ifndef __ROGUE_SCOPED_GIL_H__
#define __ROGUE_SCOPED_GIL_H__

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
#endif

namespace rogue {

   //! Logging
   class ScopedGil {

#ifndef NO_PYTHON
         PyGILState_STATE state_;
#endif

      public:
         ScopedGil();
         ~ScopedGil();
   };
}

#endif

