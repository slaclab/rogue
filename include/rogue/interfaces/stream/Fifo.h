/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Register Protocol (SRP) Fifo
 * ----------------------------------------------------------------------------
 * File          : Fifo.h
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 02/02/2018
 *-----------------------------------------------------------------------------
 * Description :
 *    AXI Stream FIFO
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
#ifndef __ROGUE_INTERFACES_STREAM_FIFO_H__
#define __ROGUE_INTERFACES_STREAM_FIFO_H__
#include <stdint.h>
#include <boost/thread.hpp>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/Logging.h>

namespace rogue {
   namespace interfaces {
      namespace stream {

         //!  AXI Stream FIFO
         class Fifo : public rogue::interfaces::stream::Master,
                      public rogue::interfaces::stream::Slave {

               rogue::LoggingPtr log_;

               // Configurations
               uint32_t trimSize_;
               uint32_t maxDepth_;

               // Queue
               rogue::Queue<boost::shared_ptr<rogue::interfaces::stream::Frame>> queue_;

               // Transmission thread
               boost::thread* thread_;

               //! Thread background
               void runThread();

            public:

               //! Class creation
               static boost::shared_ptr<rogue::interfaces::stream::Fifo> 
                  create(uint32_t maxDepth, uint32_t trimSize);

               //! Setup class in python
               static void setup_python();

               //! Creator
               Fifo(uint32_t maxDepth, uint32_t trimSize);

               //! Deconstructor
               ~Fifo();

               //! Accept a frame from master
               void acceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );

         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::stream::Fifo> FifoPtr;
      }
   }
}
#endif

