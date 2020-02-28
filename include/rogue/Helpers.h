/**
 *-----------------------------------------------------------------------------
 * Title      : Helpful Functions
 * ----------------------------------------------------------------------------
 * File       : Helpers.h
 * Created    : 2018-11-28
 * ----------------------------------------------------------------------------
 * Description:
 * Helper functions for Rogue
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
#ifndef __ROGUE_HELPERS_H__
#define __ROGUE_HELPERS_H__

// Connect stream
#define rogueStreamConnect(src,dst) src->addSlave(dst);

// Add stream tap, DEPRECATED
#define rogueStreamTap(src,dst) src->addSlave(dst);

// Connect stream bi-directionally
#define rogueStreamConnectBiDir(devA,devB) \
   devA->addSlave(devB); \
   devB->addSlave(devA);

// Connect memory bus
#define rogueBusConnect(src,dst) src->setSlave(dst);

// Global default timeout value
#define ROGUE_DEFAULT_TIMEOUT 1000000

namespace rogue {

   // Return default timeout value
   inline void defaultTimeout(struct timeval &tout) {
      div_t divResult = div(ROGUE_DEFAULT_TIMEOUT,1000000);
      tout.tv_sec  = divResult.quot;
      tout.tv_usec = divResult.rem;
   }
}



#endif

