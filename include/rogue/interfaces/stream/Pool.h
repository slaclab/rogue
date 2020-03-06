/**
 *-----------------------------------------------------------------------------
 * Title      : Stream memory pool
 * ----------------------------------------------------------------------------
 * File       : Pool.h
 * Created    : 2016-09-16
 * ----------------------------------------------------------------------------
 * Description:
 * Stream memory pool
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
#ifndef __ROGUE_INTERFACES_STREAM_POOL_H__
#define __ROGUE_INTERFACES_STREAM_POOL_H__
#include <stdint.h>

#include <thread>
#include <memory>
#include <rogue/Queue.h>
#include <rogue/EnableSharedFromThis.h>

namespace rogue {
   namespace interfaces {
      namespace stream {

         class Frame;
         class Buffer;

         //! Stream pool class
         /** The stream Pool class is responsible for allocating and garbage collecting Frame
          * objects and the Buffer objects they contain. The default mode is to allocate a
          * Frame with a single Buffer of the requested sized. Alternatively the Pool class
          * can operate in fixed buffer size mode. In this mode Buffer objects of a fixed
          * sized are allocated, with a Frame containing enough Buffer to satisfy the original
          * request. Normally Buffer data is freed when returned back to the Pool class.
          * Alternatively a pool can be enabled if operating in fixed size mode. When a pool
          * is enabled returned buffer data is stored in the pool for later allocation to
          * a new requester. The pool size defines the maximum number of entries to allow in
          * the pool.
          *
          * A subclass can be created with intercepts the Frame requests and allocates
          * Frame and Buffer objects from an alternative source such as a hardware DMA driver.
          */
         class Pool : public rogue::EnableSharedFromThis<rogue::interfaces::stream::Pool> {

               // Mutex
               std::mutex mtx_;

               // Track buffer allocations
               uint32_t allocMeta_;

               // Total memory allocated
               uint32_t allocBytes_;

               // Total buffers allocated
               uint32_t allocCount_;

               // Buffer queue
               std::queue<uint8_t *> dataQ_;

               // Fixed size buffer mode
               uint32_t fixedSize_;

               // Buffer queue count
               uint32_t poolSize_;

            public:

               // Class creator
               Pool();

               // Destroy the object
               virtual ~Pool();

               //! Get allocated memory
               /** Return the total bytes currently allocated. This value is incremented
                * as buffers are allocated and decremented as buffers are freed.
                *
                * Exposed as getAllocBytes() to Python
                * @return Total currently allocated bytes
                */
               uint32_t getAllocBytes();

               //! Get allocated buffer count
               /** Return the total number of buffers currently allocated. This value is incremented
                * as buffers are allocated and decremented as buffers are freed.
                *
                * Exposed as getAllocCount() to Python
                * @return Total currently allocated buffers
                */
               uint32_t getAllocCount();

               // Process a frame request
               /* Method to service a frame request, called by the Master class through
                * the reqFrame() method.
                *
                * size Minimum size for requested Frame, larger Frame may be allocated
                * zeroCopyEn Flag which indicates if a zero copy mode Frame is allowed.
                * Newly allocated Frame pointer (FramePtr)
                */
               virtual std::shared_ptr<rogue::interfaces::stream::Frame> acceptReq ( uint32_t size, bool zeroCopyEn );

               //! Method called to return Buffer data
               /* This method is called by the Buffer desctructor in order to free
                * the associated Buffer memory. May be overridden by a subclass to
                * change the way the buffer data is returned.
                *
                * @param data Data pointer to release
                * @param meta Meta data specific to the allocator
                * @param size Size of data buffer
                */
               virtual void retBuffer(uint8_t * data, uint32_t meta, uint32_t size);

               // Setup class for use in python
               static void setup_python();

               //! Set fixed size mode
               /** This method puts the allocator into fixed size mode.
                *
                * Exposed as setFixedSize() to Python
                * @param size Fixed size value.
                */
               void setFixedSize(uint32_t size);

               //! Get fixed size mode
               /** Return state of fixed size mode.
                *
                * Exposed as getFixedSize() to Python
                * @return Fixed size value or 0 if not in fixed size mode
                */
               uint32_t getFixedSize();

               //! Set buffer pool size
               /** Set the buffer pool size.
                *
                * Exposed as setPoolSize() to Python
                * @param size Number of entries to keep in the pool
                */
               void setPoolSize(uint32_t size);

               //! Get pool size
               /** Return configured pool size
                *
                * Exposed as getPoolSize() to Python
                * @return Pool size
                */
               uint32_t getPoolSize();

            protected:

               //! Allocate and Create a Buffer
               /** This method is the default Buffer allocator. The requested
                * buffer is created from either a malloc call or fulling a free entry from
                * the memory pool if it is enabled. If fixed size is configured the
                * size parameter is ignored and a Buffer is returned with the fixed size
                * amount of memory. The passed total value is incremented by the
                * allocated Buffer size. This method is protected to allow it to be called
                * by a sub-class of Pool.
                *
                * Not exposed to Python
                * @param size Buffer size requested
                * @param total Pointer to current total size
                * @return Allocated Buffer pointer as BufferPtr
                */
               std::shared_ptr<rogue::interfaces::stream::Buffer> allocBuffer ( uint32_t size, uint32_t *total );

               //! Create a Buffer with passed data block
               /** This method is used to create a Buffer with a pre-allocated block of
                * memory. This can be used when the block of memory is allocated by a
                * hardware DMA driver. This method is protected to allow it to be called
                * by a sub-class of Pool.
                *
                * Not exposed to Python
                * @param data Data pointer to pre-allocated memory block
                * @param meta Meta data associated with pre-allocated memory block
                * @param size Usable size of memory block (may be smaller than allocated size)
                * @param alloc Allocated size of memory block (may be greater than requested size)
                * @return Allocated Buffer pointer as BufferPtr
                */
               std::shared_ptr<rogue::interfaces::stream::Buffer> createBuffer( void * data,
                                                                                  uint32_t meta,
                                                                                  uint32_t size,
                                                                                  uint32_t alloc);

               //! Decrement Allocation counter
               /** Called in a sub-class to decrement the allocated byte count
                *
                * Not exposed to Python
                * @param alloc Amount of memory be de-allocated.
                */
               void decCounter( uint32_t alloc);

         };

         //! Alias for using shared pointer as PoolPtr
         typedef std::shared_ptr<rogue::interfaces::stream::Pool> PoolPtr;
      }
   }
}
#endif

