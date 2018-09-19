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

#include <rogue/interfaces/stream/Frame.h>

namespace rogue {
   namespace interfaces {
      namespace stream {

         class Pool;
         class Frame;

         //! Frame buffer
         /*
          * This class is a container for buffers which make up a frame.
          * Each buffer within the frame has a reserved header area and a 
          * payload. 
         */
         class Buffer {

               //! Pointer to entity which allocated this buffer
               boost::shared_ptr<rogue::interfaces::stream::Pool> source_;

               //! Pointer to frame containing this buffer
               boost::weak_ptr<rogue::interfaces::stream::Frame> frame_;

               //! Pointer to raw data buffer. Raw pointer is used here!
               uint8_t *  data_;

               //! Meta data used to track this buffer by source
               uint32_t   meta_;

               //! Alloc size of buffer, alloc may be greater than raw size due to buffer alloctor
               uint32_t   allocSize_;

               //! Raw size of buffer, size as requested, alloc may be greater
               uint32_t   rawSize_;

               //! Header room of buffer
               uint32_t   headRoom_;

               //! Tail room of buffer, used to keep payload from using up tail space
               uint32_t   tailRoom_;

               //! Data count including header
               uint32_t  payload_;

               //! Interface specific flags
               uint32_t   flags_;

               //! Error state
               uint32_t   error_;

            public:

               //! Iterator for data
               typedef uint8_t * iterator;

               //! Class creation
               /*
                * Pass owner, raw data buffer, and meta data
                */
               static boost::shared_ptr<rogue::interfaces::stream::Buffer> create (
                     boost::shared_ptr<rogue::interfaces::stream::Pool> source, 
                        void * data, uint32_t meta, uint32_t size, uint32_t alloc);

               //! Create a buffer.
               /*
                * Pass owner, raw data buffer, and meta data
                */
               Buffer(boost::shared_ptr<rogue::interfaces::stream::Pool> source, 
                      void * data, uint32_t meta, uint32_t size, uint32_t alloc);

               //! Destroy a buffer
               /*
                * Owner return buffer method is called
                */
               ~Buffer();

               //! Set ownder frame
               void setFrame(boost::shared_ptr<rogue::interfaces::stream::Frame> frame);

               //! Get meta data, used by pool
               uint32_t getMeta();

               //! Set meta data, used by pool
               void setMeta(uint32_t meta);

               //! Adjust header by passed value
               void adjustHeader(int32_t value);

               //! Clear the header reservation
               void zeroHeader();

               //! Adjust tail by passed value
               void adjustTail(int32_t value);

               //! Clear the tail reservation
               void zeroTail();

               /* 
                * Get data pointer (begin iterator)
                * Returns base + header size
                */
               uint8_t * begin();

               /*
                * Get end data pointer (end iterator)
                * This is the end of raw data buffer
                */
               uint8_t * end();

               /*
                * Get end payload pointer (end iterator)
                * This is the end of payload data
                */
               uint8_t * endPayload();

               /*
                * Get size of buffer that can hold
                * payload data. This function 
                * returns the full buffer size minus
                * the head and tail reservation.
                */
               uint32_t getSize();

               /*
                * Get available size for payload
                * This is the space remaining for payload
                * minus the space reserved for the tail
                */
               uint32_t getAvailable();

               /*
                * Get real payload size without header
                * This is the count of real data in the 
                * packet, minus the portion reserved for
                * the head.
                */
               uint32_t getPayload();

               /* Set payload size (not including header) */
               void setPayload(uint32_t size);

               /* 
                * Set min payload size (not including header)
                * Payload size is updated only if size > current size
                */
               void minPayload(uint32_t size);

               //! Adjust payload size
               void adjustPayload(int32_t value);

               //! Set the buffer as full (minus tail reservation)
               void setPayloadFull();

               //! Set the buffer as empty (minus header reservation)
               void setPayloadEmpty();
         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::stream::Buffer> BufferPtr;
      }
   }
}

#endif

