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

#include <boost/python.hpp>
#include <boost/thread.hpp>
#include <boost/enable_shared_from_this.hpp>

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

               //! Track buffer free
               uint32_t freeMeta_;

               //! Total memory allocated
               uint32_t allocBytes_;

               //! Total buffers allocated
               uint32_t allocCount_;

            protected:

               //! Create a frame
               /*
                * Pass total size of frame. Zero for empty frame
                * Pass per buffer size.
                * If compact is set buffers are allocated based upon needed size.
                * If compact is not set, all buffers are allocated with size = buffSize
                * Pass zero copy flag
                */
               boost::shared_ptr<rogue::interfaces::stream::Frame> createFrame ( uint32_t totSize, 
                                                                                 uint32_t buffSize,
                                                                                 bool compact,
                                                                                 bool zeroCopy );

               //! Allocate and Create a Buffer
               boost::shared_ptr<rogue::interfaces::stream::Buffer> allocBuffer ( uint32_t size );

               //! Create a Buffer with passed data
               boost::shared_ptr<rogue::interfaces::stream::Buffer> createBuffer( void * data, 
                                                                                  uint32_t meta, 
                                                                                  uint32_t rawSize);

               //! Delete a buffer
               void deleteBuffer( uint32_t rawSize);

            public:

               //! Setup class in python
               static void setup_python();

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
                * maxBuffSize indicates the largest acceptable buffer size. A larger buffer can be
                * returned but the total buffer count must assume each buffer is of size maxBuffSize
                * If maxBuffSize = 0, slave will freely determine the buffer size.
                */
               virtual boost::shared_ptr<rogue::interfaces::stream::Frame>
                  acceptReq ( uint32_t size, bool zeroCopyEn, uint32_t maxBuffSize );

               //! Return a buffer
               /*
                * Called when this instance is marked as owner of a Buffer entity that is deleted.
                */
               virtual void retBuffer(uint8_t * data, uint32_t meta, uint32_t rawSize);
         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::stream::Pool> PoolPtr;
      }
   }
}
#endif

