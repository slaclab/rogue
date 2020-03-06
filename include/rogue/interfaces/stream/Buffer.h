/**
 *-----------------------------------------------------------------------------
 * Title      : Stream Buffer Container
 * ----------------------------------------------------------------------------
 * File       : Buffer.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
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
         /** This class is a container for buffers which make up a frame. Each buffer is associated
          * with a contiguous block of memory allocated by an instance of the Pool class.
          * Each buffer within the frame has a reserved header and tail area to pre-reserve
          * space which may be required by protocol layers. Direct interaction with the Buffer
          * class is an advanced topic, most users will simply use a FrameIterator to access
          * Frame and Buffer data. The Buffer class is not available in Python.
         */
         class Buffer {

               // Pointer to entity which allocated this buffer
               std::shared_ptr<rogue::interfaces::stream::Pool> source_;

               // Pointer to frame containing this buffer
               std::weak_ptr<rogue::interfaces::stream::Frame> frame_;

               // Pointer to raw data buffer. Raw pointer is used here!
               uint8_t *  data_;

               // Meta data used to track this buffer by source
               uint32_t   meta_;

               // Alloc size of buffer, alloc may be greater than raw size due to buffer allocator
               uint32_t   allocSize_;

               // Raw size of buffer, size as requested, alloc may be greater
               uint32_t   rawSize_;

               // Header room of buffer
               uint32_t   headRoom_;

               // Tail room of buffer, used to keep payload from using up tail space
               uint32_t   tailRoom_;

               // Data count including header
               uint32_t  payload_;

               // Interface specific flags
               uint32_t   flags_;

               // Error state
               uint32_t   error_;

            public:

               //! Alias for using uint8_t * as Buffer::iterator
               typedef uint8_t * iterator;

               // Class factory which returns a BufferPtr
               /* Create a new Buffer with associated data.
                *
                * Not exposed to python, Called by Pool class
                * data Pointer to raw data block associated with Buffer
                * meta Meta data to track allocation
                * size Size of raw data block usable by Buffer
                * alloc Total memory allocated, may be greater than size
                */
               static std::shared_ptr<rogue::interfaces::stream::Buffer> create (
                     std::shared_ptr<rogue::interfaces::stream::Pool> source,
                        void * data, uint32_t meta, uint32_t size, uint32_t alloc);

               // Create a buffer.
               Buffer(std::shared_ptr<rogue::interfaces::stream::Pool> source,
                      void * data, uint32_t meta, uint32_t size, uint32_t alloc);

               // Destroy a buffer
               ~Buffer();

               // Set owner frame, called by Frame class only
               void setFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

               //! Get meta data
               /** The meta data field is used by the Pool class or sub-class to
                * track the allocated data.
                * @return Meta data value
                */
               uint32_t getMeta();

               //! Set meta data
               /** The meta data field is used by the Pool class or sub-class to
                * track the allocated data.
                * @param meta Meta data value
                */
               void setMeta(uint32_t meta);

               //! Adjust header by passed value
               /** @param value Head adjustment amount
                */
               void adjustHeader(int32_t value);

               //! Clear the header reservation
               void zeroHeader();

               //! Adjust tail reservation by passed value
               /** @param value Tail adjustment amount
                */
               void adjustTail(int32_t value);

               //! Clear the tail reservation
               void zeroTail();

               //! Get beginning buffer iterator
               /** Get an iterator which indicates the start of the
                * buffer space, not including the header reservation.
                * @return Begin buffer iterator
                */
               uint8_t * begin();

               //! Get end buffer iterator
               /** Get an iterator which indicates the end of the the buffer minus
                * the tail reservation.
                * @return End buffer iterator
                */
               uint8_t * end();

               //! Get end payload iterator
               /** Get an iterator which indicates the end of the the payload space.
                * @return End payload iterator
                */
               uint8_t * endPayload();

               //! Get Buffer size
               /** Get size of buffer that can hold payload data. This function
                * returns the full buffer size minus the head and tail reservation.
                * @return Buffer size in bytes
                */
               uint32_t getSize();

               //! Get the available space for payload
               /** Get the remaining data available for payload.
                * @return The amount of available space for payload in bytes.
                */
               uint32_t getAvailable();

               //! Get the payload size
               /** This method will return the amount of
                * payload data in the buffer.
                * @return Payload size in bytes
                */
               uint32_t getPayload();

               //! Set the payload size
               /** Set the payload size to the passed value.
                * @param size New payload size in bytes
                */
               void setPayload(uint32_t size);

               //! Set minimum payload size.
               /** This method sets the payload size to be at least
                * the passed value. If the current payload size exceeds
                * the passed value, the size is unchanged.
                * @param size Min payload size in bytes
                */
               void minPayload(uint32_t size);

               //! Adjust the payload size
               /** This method adjusts the payload size by the
                * passed positive or negative value.
                * @param value Value to adjust payload by in bytes
                */
               void adjustPayload(int32_t value);

               //! Set the payload size to fill the buffer
               /**This method sets the buffer payload size to fill the buffer,
                * minus the header and tail reservation.
                */
               void setPayloadFull();

               //! Set the buffer as empty
               /**This method sets the buffer payload size as empty.
                */
               void setPayloadEmpty();

               //! Debug Buffer
               void debug(uint32_t idx);
         };

         //! Alias for using shared pointer as BufferPtr
         typedef std::shared_ptr<rogue::interfaces::stream::Buffer> BufferPtr;
      }
   }
}

#endif

