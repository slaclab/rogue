/**
 *-----------------------------------------------------------------------------
 * Title         : Rogue stream de-compressor
 * ----------------------------------------------------------------------------
 * File          : StreamUnZip.h
 *-----------------------------------------------------------------------------
 * Description :
 *    Stream modules to decompress a data stream
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
#ifndef __ROGUE_UTILITIES_STREAM_UN_ZIP_H__
#define __ROGUE_UTILITIES_STREAM_UN_ZIP_H__
#include <stdint.h>
#include <thread>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/stream/Master.h>

namespace rogue {
   namespace utilities {

      //! Stream compressor
      class StreamUnZip : public rogue::interfaces::stream::Slave, public rogue::interfaces::stream::Master {

         public:

            //! Class creation
            static std::shared_ptr<rogue::utilities::StreamUnZip> create ();

            //! Setup class in python
            static void setup_python();

            //! Creator
            StreamUnZip();

            //! Deconstructor
            ~StreamUnZip();

            //! Accept a frame from master
            void acceptFrame ( std::shared_ptr<rogue::interfaces::stream::Frame> frame );

            //! Accept a new frame request
            std::shared_ptr<rogue::interfaces::stream::Frame> acceptReq ( uint32_t size, bool zeroCopyEn );
      };

      // Convenience
      typedef std::shared_ptr<rogue::utilities::StreamUnZip> StreamUnZipPtr;
   }
}
#endif

