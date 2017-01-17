/**
 *-----------------------------------------------------------------------------
 * Title      : Stream Buffer Container
 * ----------------------------------------------------------------------------
 * File       : Buffer.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-09-16
 * Last update: 2016-09-16
 * ----------------------------------------------------------------------------
 * Description:
 * Stream frame container
 * Some concepts borrowed from CPSW by Till Straumann
 * TODO:
 *    Add locking for thread safety. May not be needed since the source will
 *    set things up once before handing off to the various threads.
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
#ifndef __ROGUE_INTERFACES_STREAM_BUFFER_H__
#define __ROGUE_INTERFACES_STREAM_BUFFER_H__
#include <stdint.h>

#include <boost/python.hpp>
namespace rogue {
   namespace interfaces {
      namespace stream {

         class Pool;

         //! Frame buffer
         /*
          * This class is a container for buffers which make up a frame.
          * Each buffer within the frame has a reserved header area and a 
          * payload. 
         */
         class Buffer {

               //! Pointer to entity which allocated this buffer
               boost::shared_ptr<rogue::interfaces::stream::Pool> source_; 

               //! Pointer to raw data buffer. Raw pointer is used here!
               uint8_t *  data_;

               //! Meta data used to track this buffer by source
               uint32_t   meta_;

               //! Raw size of buffer
               uint32_t   rawSize_;

               //! Header room of buffer
               uint32_t   headRoom_;

               //! Data count including header
               uint32_t   count_;

               //! Interface specific flags
               uint32_t   flags_;

               //! Error state
               uint32_t   error_;

            public:

               //! Class creation
               /*
                * Pass owner, raw data buffer, and meta data
                */
               static boost::shared_ptr<rogue::interfaces::stream::Buffer> create (
                     boost::shared_ptr<rogue::interfaces::stream::Pool> source, 
                        void * data, uint32_t meta, uint32_t rawSize);

               //! Setup class in python
               static void setup_python();

               //! Create a buffer.
               /*
                * Pass owner, raw data buffer, and meta data
                */
               Buffer(boost::shared_ptr<rogue::interfaces::stream::Pool> source, 
                      void * data, uint32_t meta, uint32_t rawSize);

               //! Destroy a buffer
               /*
                * Owner return buffer method is called
                */
               ~Buffer();

               //! Get raw data pointer
               uint8_t * getRawData();

               //! Get payload data pointer
               uint8_t * getPayloadData();

               //! Get meta data
               uint32_t getMeta();

               //! Set meta data
               void setMeta(uint32_t meta);

               //! Get raw size
               uint32_t getRawSize();

               //! Get buffer data count (payload + headroom)
               uint32_t getCount();

               //! Get header space
               uint32_t getHeadRoom();

               //! Get available size for payload
               uint32_t getAvailable();

               //! Get real payload size without header
               uint32_t getPayload();

               //! Get flags
               uint32_t getFlags();

               //! Set flags
               void setFlags(uint32_t flags);

               //! Get error state
               uint32_t getError();

               //! Set error state
               void setError(uint32_t error);

               //! Set size including header
               void setSize(uint32_t size);

               //! Set payload size (not including header)
               void setPayload(uint32_t size);

               //! Set head room
               void setHeadRoom(uint32_t offset);

         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::stream::Buffer> BufferPtr;
      }
   }
}

#endif

