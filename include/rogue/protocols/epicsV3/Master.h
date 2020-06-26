/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue EPICS V3 Interface: Master Stream Interface
 * ----------------------------------------------------------------------------
 * File       : Master.h
 * Created    : 2018-11-18
 * ----------------------------------------------------------------------------
 * Description:
 * Rogue stream master interface for EPICs variables
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

#ifndef __ROGUE_PROTOCOLS_EPICSV3_MASTER_H__
#define __ROGUE_PROTOCOLS_EPICSV3_MASTER_H__

#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
#include <thread>
#include <casdef.h>
#include <gdd.h>
#include <gddApps.h>
#include <gddAppFuncTable.h>
#include <rogue/protocols/epicsV3/Value.h>
#include <rogue/interfaces/stream/Master.h>

namespace rogue {
   namespace protocols {
      namespace epicsV3 {

         class Master: public Value, public rogue::interfaces::stream::Master {
            public:

               //! Setup class in python
               static void setup_python();

               //! Class creation
               Master ( std::string epicsName, uint32_t max, std::string type );

               ~Master ();

               bool valueGet();

               bool valueSet();
         };

         // Convienence
         typedef std::shared_ptr<rogue::protocols::epicsV3::Master> MasterPtr;

      }
   }
}

#endif

