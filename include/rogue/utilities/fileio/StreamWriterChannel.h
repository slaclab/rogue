/**
 *-----------------------------------------------------------------------------
 * Title         : Data file writer utility. Channel interface.
 *-----------------------------------------------------------------------------
 * Description :
 *    Class to act as a slave interface to the StreamWriter. Each
 *    slave is associated with a tag. The tag is included in the bank header
 *    of each write.
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
#ifndef __ROGUE_UTILITIES_FILEIO_STREAM_WRITER_CHANNEL_H__
#define __ROGUE_UTILITIES_FILEIO_STREAM_WRITER_CHANNEL_H__
#include <stdint.h>
#include <thread>
#include <rogue/interfaces/stream/Slave.h>

namespace rogue {
   namespace utilities {
      namespace fileio {

         class StreamWriter;

         //! Stream writer central class
         class StreamWriterChannel : public rogue::interfaces::stream::Slave {

               //! Associated Stream Writer class
               std::shared_ptr<rogue::utilities::fileio::StreamWriter> writer_;

               //! Channel information
               uint8_t channel_;

               //! Number of frames received by channel
               uint32_t frameCount_;

               //! Lock for frameCount_
               std::mutex mtx_;

               //! Condition variable for frameCount_ updates
               std::condition_variable cond_;

            public:

               //! Class creation
               static std::shared_ptr<rogue::utilities::fileio::StreamWriterChannel>
                  create (std::shared_ptr<rogue::utilities::fileio::StreamWriter> writer, uint8_t channel);

               //! Setup class in python
               static void setup_python();

               //! Creator
               StreamWriterChannel(std::shared_ptr<rogue::utilities::fileio::StreamWriter> writer, uint8_t channel);

               //! Deconstructor
               ~StreamWriterChannel();

               //! Accept a frame from master
               void acceptFrame ( std::shared_ptr<rogue::interfaces::stream::Frame> frame );

               //! Get number of frames that have been accepted
               uint32_t getFrameCount();

               //! Set the frame count to a specific value
               void setFrameCount(uint32_t count);

               //! Block until a number of frames have been received
               bool waitFrameCount(uint32_t count, uint64_t timeout);
         };

         // Convenience
         typedef std::shared_ptr<rogue::utilities::fileio::StreamWriterChannel> StreamWriterChannelPtr;
      }
   }
}

#endif

