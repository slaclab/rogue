/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Register Protocol (SRP) Filter
 * ----------------------------------------------------------------------------
 * File          : Filter.h
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 11/01/2018
 *-----------------------------------------------------------------------------
 * Description :
 *    AXI Stream Filter
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
#ifndef __ROGUE_INTERFACES_STREAM_FILTER_H__
#define __ROGUE_INTERFACES_STREAM_FILTER_H__
#include <stdint.h>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/Logging.h>

namespace rogue {
   namespace interfaces {
      namespace stream {

         //!  AXI Stream FIFO
         class Filter : public rogue::interfaces::stream::Master,
                        public rogue::interfaces::stream::Slave {

               rogue::LoggingPtr log_;

               // Configurations
               bool     dropErrors_;
               uint8_t  channel_;

            public:

               //! Class creation
               static boost::shared_ptr<rogue::interfaces::stream::Filter> create(bool dropErrors, uint8_t channel);

               //! Setup class in python
               static void setup_python();

               //! Creator
               Filter(bool dropErrors, uint8_t channel);

               //! Deconstructor
               ~Filter();

               //! Accept a frame from master
               void acceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );

         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::stream::Filter> FilterPtr;
      }
   }
}
#endif

