/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Batcher Data Container
 * ----------------------------------------------------------------------------
 * File          : Data.h
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 02/08/2019
 *-----------------------------------------------------------------------------
 * Description :
 *    AXI Batcher Data
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
#ifndef __ROGUE_PROTOCOLS_BATCHER_DATA_H__
#define __ROGUE_PROTOCOLS_BATCHER_DATA_H__
#include <stdint.h>
#include <thread>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/FrameIterator.h>

namespace rogue {
   namespace protocols {
      namespace batcher {

         //!  AXI Stream FIFO
         class Data {

               //! Data Iterator
               rogue::interfaces::stream::FrameIterator it_;

               //! Data Size
               uint32_t size_;

               //! Data destination
               uint8_t dest_;

               //! First user
               uint8_t fUser_;

               //! Last user
               uint8_t lUser_;

            public:

               //! Setup class in python
               static void setup_python();

               //! Create object
               static std::shared_ptr<rogue::protocols::batcher::Data> create (
                  rogue::interfaces::stream::FrameIterator it,
                  uint32_t size, uint8_t dest, uint8_t fUser, uint8_t lUser);

               //! Creator
               Data(rogue::interfaces::stream::FrameIterator it,
                    uint32_t size, uint8_t dest, uint8_t fUser, uint8_t lUser);

               //! Deconstructor
               ~Data();

               //! Return Begin Data Iterator
               rogue::interfaces::stream::FrameIterator begin();

               //! Return End Data Iterator
               rogue::interfaces::stream::FrameIterator end();

               //! Return Data Size
               uint32_t size();

               //! Return Data destination
               uint8_t dest();

               //! Return First user
               uint8_t fUser();

               //! Return Last user
               uint8_t lUser();

         };

         // Convienence
         typedef std::shared_ptr<rogue::protocols::batcher::Data> DataPtr;
      }
   }
}
#endif

