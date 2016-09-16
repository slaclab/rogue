/**
 *-----------------------------------------------------------------------------
 * Title      : Stream Buffer Container
 * ----------------------------------------------------------------------------
 * File       : StreamBuffer.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-08-08
 * Last update: 2016-08-08
 * ----------------------------------------------------------------------------
 * Description:
 * Stream frame container
 * Some concepts borrowed from CPSW by Till Straumann
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
#ifndef __INTERFACES_STREAM_BUFFER_H__
#define __INTERFACES_STREAM_BUFFER_H__
#include <stdint.h>

#include <boost/python.hpp>
namespace interfaces {
   namespace stream {

      class Slave;

      //! Frame buffer
      /*
       * This class is a container for buffers which make up a frame.
       * Each buffer within the frame has a reserved header area and a 
       * payload.
      */
      class Buffer {
            boost::shared_ptr<interfaces::stream::Slave> source_; //! Pointer to entity which allocated this buffer

            uint8_t *  data_;     //! Pointer to raw data buffer. Raw pointer is used here!
            uint32_t   meta_;     //! Meta data used to track this buffer by source
            uint32_t   rawSize_;  //! Raw size of buffer
            uint32_t   headRoom_; //! Header room of buffer
            uint32_t   count_;    //! Data count including header
            uint32_t   error_;    //! Error state

         public:

            //! Class creation
            /*
             * Pass owner, raw data buffer, and meta data
             */
            static boost::shared_ptr<interfaces::stream::Buffer> create (
                  boost::shared_ptr<interfaces::stream::Slave> source, 
                     void * data, uint32_t meta, uint32_t rawSize);

            //! Create a buffer.
            /*
             * Pass owner, raw data buffer, and meta data
             */
            Buffer(boost::shared_ptr<interfaces::stream::Slave> source, void * data, uint32_t meta, uint32_t rawSize);

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

            //! Get raw size
            uint32_t getRawSize();

            //! Get header space
            uint32_t getHeadRoom();

            //! Get available size for payload
            uint32_t getAvailable();

            //! Get real payload size
            uint32_t getPayload();

            //! Get error state
            uint32_t getError();

            //! Set error state
            void setError(uint32_t error);

            //! Set size including header
            void setSetSize(uint32_t size);

            //! Set head room
            void setHeadRoom(uint32_t offset);

            //! Read up to count bytes from buffer, starting from offset.
            uint32_t read  ( void *p, uint32_t offset, uint32_t count );

            //! Write count bytes to frame, starting at offset
            uint32_t write ( void *p, uint32_t offset, uint32_t count );

      };

      // Convienence
      typedef boost::shared_ptr<interfaces::stream::Buffer> BufferPtr;
   }
}

#endif

