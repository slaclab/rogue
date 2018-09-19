/**
 *-----------------------------------------------------------------------------
 * Title      : Stream memory pool
 * ----------------------------------------------------------------------------
 * File       : Pool.h
 * Created    : 2016-09-16
 * ----------------------------------------------------------------------------
 * Description:
 * Stream memory pool
 * TODO:
 *    Create central memory pool allocator for proper allocate and free of
 *    buffers and frames.
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

#include <boost/thread.hpp>
#include <boost/enable_shared_from_this.hpp>
#include <rogue/Queue.h>

namespace rogue {
   namespace interfaces {
      namespace stream {

         class Frame;
         class Buffer;

         //! Stream pool class
         class Pool : public boost::enable_shared_from_this<rogue::interfaces::stream::Pool> {

               //! Mutex
               boost::mutex mtx_;

               //! Track buffer allocations
               uint32_t allocMeta_;

               //! Total memory allocated
               uint32_t allocBytes_;

               //! Total buffers allocated
               uint32_t allocCount_;

               //! Buffer queue
               std::queue<uint8_t *> dataQ_;

               //! Fixed size buffer mode
               uint32_t fixedSize_;

               //! Buffer queue count
               uint32_t poolSize_;

            public:

               //! Creator
               Pool();

               //! Destructor
               virtual ~Pool();

               //! Get allocated memory
               uint32_t getAllocBytes();

               //! Get allocated count
               uint32_t getAllocCount();

               //! Generate a Frame. Called from master
               /*
                * Pass total size required.
                * Pass flag indicating if zero copy buffers are acceptable
                */
               virtual boost::shared_ptr<rogue::interfaces::stream::Frame> acceptReq ( uint32_t size, bool zeroCopyEn );

               //! Return a buffer
               /*
                * Called when this instance is marked as owner of a Buffer entity that is deleted.
                */
               virtual void retBuffer(uint8_t * data, uint32_t meta, uint32_t size);

               //! Setup class in python
               static void setup_python();

               //! Set fixed size mode
               void setFixedSize(uint32_t size);
               
               //! Get fixed size mode
               uint32_t getFixedSize();

               //! Set buffer pool size
               void setPoolSize(uint32_t size);
               
               //! Get pool size
               uint32_t getPoolSize();

            protected:

               //! Allocate and Create a Buffer
               boost::shared_ptr<rogue::interfaces::stream::Buffer> allocBuffer ( uint32_t size, uint32_t *total );

               //! Create a Buffer with passed data
               boost::shared_ptr<rogue::interfaces::stream::Buffer> createBuffer( void * data, 
                                                                                  uint32_t meta, 
                                                                                  uint32_t size,
                                                                                  uint32_t alloc);

               //! Decrement Allocation counter
               void decCounter( uint32_t alloc);

         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::stream::Pool> PoolPtr;
      }
   }
}
#endif

