/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue EPICS V3 Interface: Module Setup
 * ----------------------------------------------------------------------------
 * File       : module.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2018-01-31
 * ----------------------------------------------------------------------------
 * Description:
 * Python module setup
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
#ifndef __ROGUE_PROTOCOLS_EPICSV3_MODULE_H__
#define __ROGUE_PROTOCOLS_EPICSV3_MODULE_H__

namespace rogue {
   namespace protocols {
      namespace epicsV3 {
         void setup_module();
      }
   }
}

#endif

