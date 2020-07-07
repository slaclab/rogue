/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Batcher Version 1, Core
 * ----------------------------------------------------------------------------
 * File          : Core.h
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 10/26/2018
 *-----------------------------------------------------------------------------
 * Description :
 *    AXI Batcher V1
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
#ifndef __ROGUE_PROTOCOLS_BATCHER_CORE_V1_H__
#define __ROGUE_PROTOCOLS_BATCHER_CORE_V1_H__
#include <stdint.h>
#include <thread>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/Logging.h>

namespace rogue {
   namespace protocols {
      namespace batcher {

         class Data;

         //!  AXI Stream FIFO
         class CoreV1 {

               std::shared_ptr<rogue::Logging> log_;

               //! Frame pointers
               std::shared_ptr<rogue::interfaces::stream::Frame> frame_;

               //! Data List
               std::vector< std::shared_ptr<rogue::protocols::batcher::Data> > list_;

               //! Header size
               uint32_t headerSize_;

               //! Tail size
               uint32_t tailSize_;

               //! Tail pointers
               std::vector<rogue::interfaces::stream::FrameIterator> tails_;

               //! Sequence number
               uint32_t seq_;

            public:

               //! Setup class in python
               static void setup_python();

               //! Create class
               static std::shared_ptr<rogue::protocols::batcher::CoreV1> create();

               //! Creator
               CoreV1();

               //! Deconstructor
               ~CoreV1();

               //! Init size for internal containers
               void initSize(uint32_t size);

               //! Record count
               uint32_t count();

               //! Get header size
               uint32_t headerSize();

               //! Get beginning of header iterator
               rogue::interfaces::stream::FrameIterator beginHeader();

               //! Get end of header iterator
               rogue::interfaces::stream::FrameIterator endHeader();

               //! Get tail size
               uint32_t tailSize();

               //! Get beginning of tail iterator
               rogue::interfaces::stream::FrameIterator beginTail(uint32_t index);

               //! Get end of tail iterator
               rogue::interfaces::stream::FrameIterator endTail(uint32_t index);

               //! Get data
               std::shared_ptr<rogue::protocols::batcher::Data> & record(uint32_t index);

               //! Return sequence
               uint32_t sequence();

               //! Process a frame
               bool processFrame ( std::shared_ptr<rogue::interfaces::stream::Frame> frame );

               //! Reset data
               void reset();
         };

         // Convienence
         typedef std::shared_ptr<rogue::protocols::batcher::CoreV1> CoreV1Ptr;
      }
   }
}
#endif

