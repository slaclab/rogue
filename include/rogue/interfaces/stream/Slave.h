/**
 *-----------------------------------------------------------------------------
 * Title      : Stream interface slave
 * ----------------------------------------------------------------------------
 * File       : Slave.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-09-16
 * Last update: 2016-09-16
 * ----------------------------------------------------------------------------
 * Description:
 * Stream interface slave
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
#ifndef __ROGUE_INTERFACES_STREAM_SLAVE_H__
#define __ROGUE_INTERFACES_STREAM_SLAVE_H__
#include <stdint.h>

#include <boost/python.hpp>
#include <boost/enable_shared_from_this.hpp>
#include <boost/thread.hpp>

namespace rogue {
   namespace interfaces {
      namespace stream {

         class Frame;
         class Buffer;

         //! Stream slave class
         /*
          * The stream slave accepts stream data from a master. It also
          * can accept frame allocation requests.
          */
         class Slave : public boost::enable_shared_from_this<rogue::interfaces::stream::Slave> {

               //! Meta mutex
               boost::mutex metaMtx_;

               //! Alloc mutex
               boost::mutex allocMtx_;

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

               //! Class creation
               static boost::shared_ptr<rogue::interfaces::stream::Slave> create ();

               //! Setup class in python
               static void setup_python();

               //! Creator
               Slave();

               //! Destructor
               virtual ~Slave();

               //! Get allocated memory
               uint32_t getAllocBytes();

               //! Get allocated count
               uint32_t getAllocCount();

               //! Generate a Frame. Called from master
               /*
                * Pass total size required.
                * Pass flag indicating if zero copy buffers are acceptable
                * Pass timeout in microseconds or zero to wait forever
                */
               virtual boost::shared_ptr<rogue::interfaces::stream::Frame>
                  acceptReq ( uint32_t size, bool zeroCopyEn, uint32_t timeout);

               //! Accept a frame from master
               /* 
                * Returns true on success
                * Pass timeout in microseconds or zero to wait forever
                */
               virtual bool acceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame, 
                                          uint32_t timeout );

               //! Return a buffer
               /*
                * Called when this instance is marked as owner of a Buffer entity that is deleted.
                */
               virtual void retBuffer(uint8_t * data, uint32_t meta, uint32_t rawSize);
         };

         //! Stream slave class, wrapper to enable pyton overload of virtual methods
         class SlaveWrap : 
            public rogue::interfaces::stream::Slave, 
            public boost::python::wrapper<rogue::interfaces::stream::Slave> {

            public:

               //! Accept frame
               bool acceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame, uint32_t timeout );

               //! Default accept frame call
               bool defAcceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame, uint32_t timeout );
         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::stream::Slave> SlavePtr;
         typedef boost::shared_ptr<rogue::interfaces::stream::SlaveWrap> SlaveWrapPtr;
      }
   }
}
#endif

