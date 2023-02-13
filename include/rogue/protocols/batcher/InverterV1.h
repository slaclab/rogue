/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Inverter Version 1
 * ----------------------------------------------------------------------------
 * File          : InverterV1.h
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 10/26/2018
 *-----------------------------------------------------------------------------
 * Description :
 *    AXI Inverter V1
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
#ifndef __ROGUE_PROTOCOLS_BATCHER_INVERTER_V1_H__
#define __ROGUE_PROTOCOLS_BATCHER_INVERTER_V1_H__
#include <stdint.h>
#include <thread>
#include <memory>
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/Logging.h"

namespace rogue {
   namespace protocols {
      namespace batcher {

         //!  AXI Stream FIFO
         class InverterV1 : public rogue::interfaces::stream::Master,
                            public rogue::interfaces::stream::Slave {

            public:

               //! Class creation
               static std::shared_ptr<rogue::protocols::batcher::InverterV1> create();

               //! Setup class in python
               static void setup_python();

               //! Creator
               InverterV1();

               //! Deconstructor
               ~InverterV1();

               //! Accept a frame from master
               void acceptFrame ( std::shared_ptr<rogue::interfaces::stream::Frame> frame );

         };

         // Convienence
         typedef std::shared_ptr<rogue::protocols::batcher::InverterV1> InverterV1Ptr;
      }
   }
}
#endif

