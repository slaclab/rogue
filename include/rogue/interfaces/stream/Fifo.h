/**
 *-----------------------------------------------------------------------------
 * Title         : AXI Stream FIFO
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
#include <thread>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/Logging.h>

namespace rogue {
   namespace interfaces {
      namespace stream {

         //! Stream Frame FIFO
         /** The stream Fifo object buffers Frame data as it is received from a
          * Master. It is then passed to the attached Slave objects in an independent
          * thread.
          *
          * The Fifo can either store the original data or create a copy of the
          * data in a new Frame.
          *
          * The copied data can be configured to be a fixed size to limit the amount of
          * data copied.
          *
          * The Fifo supports a maximum depth to be configured. After this depth is reached
          * new incoming Frame objects are dropped.
          */
         class Fifo : public rogue::interfaces::stream::Master,
                      public rogue::interfaces::stream::Slave {

               std::shared_ptr<rogue::Logging> log_;

               // Configurations
               uint32_t maxDepth_;
               uint32_t trimSize_;
               bool     noCopy_;

               // Drop frame counter
               std::size_t dropFrameCnt_;

               // Queue
               rogue::Queue<std::shared_ptr<rogue::interfaces::stream::Frame>> queue_;

               // Transmission thread
               bool threadEn_;
               std::thread* thread_;

               // Thread background
               void runThread();

            public:

               //! Create a Fifo object and return as a FifoPtr
               /** Exposed as rogue.interfaces.stream.Fifo() to Python
                * @param maxDepth Set to a non-zero value to configured fixed size mode.
                * @param trimSize Set to a non-zero value to limit the amount of data copied.
                * @param noCopy Set to true to disable Frame copy
                * @return Fifo object as a FifoPtr
                */
               static std::shared_ptr<rogue::interfaces::stream::Fifo>
                  create(uint32_t maxDepth, uint32_t trimSize, bool noCopy);

               // Setup class for use in python
               static void setup_python();

               // Create a Fifo object.
               Fifo(uint32_t maxDepth, uint32_t trimSize, bool noCopy);

               // Destroy the Fifo
               ~Fifo();

               // Return the number of elements in the Fifo
               std::size_t size();

               // Return the number of dropped frames
               std::size_t dropCnt() const;

               // Clear counters
               void clearCnt();

               // Receive frame from Master
               void acceptFrame ( std::shared_ptr<rogue::interfaces::stream::Frame> frame );

         };

         //! Alias for using shared pointer as FifoPtr
         typedef std::shared_ptr<rogue::interfaces::stream::Fifo> FifoPtr;
      }
   }
}
#endif

