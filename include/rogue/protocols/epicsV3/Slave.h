/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue EPICS V3 Interface: Stream Slave Interface
 * ----------------------------------------------------------------------------
 * File       : Slave.h
 * Created    : 2018-11-18
 * ----------------------------------------------------------------------------
 * Description:
 * Stream slave to epics variables
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

#ifndef __ROGUE_PROTOCOLS_EPICSV3_SLAVE_H__
#define __ROGUE_PROTOCOLS_EPICSV3_SLAVE_H__

#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
#include <thread>
#include <casdef.h>
#include <gdd.h>
#include <gddApps.h>
#include <gddAppFuncTable.h>
#include <rogue/protocols/epicsV3/Value.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/stream/Frame.h>

namespace rogue {
   namespace protocols {
      namespace epicsV3 {

         class Slave: public Value, public rogue::interfaces::stream::Slave {
            public:

               //! Setup class in python
               static void setup_python();

               //! Class creation
               Slave ( std::string epicsName, uint32_t max, std::string type );

               ~Slave ();

               // Lock held when called
               bool valueGet();

               // Lock held when called
               bool valueSet();

               //! Accept a frame from master
               void acceptFrame ( std::shared_ptr<rogue::interfaces::stream::Frame> frame );
         };

         // Convienence
         typedef std::shared_ptr<rogue::protocols::epicsV3::Slave> SlavePtr;

      }
   }
}

#endif

