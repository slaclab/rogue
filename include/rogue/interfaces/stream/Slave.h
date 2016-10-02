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

               //! Debug control
               uint32_t    debug_;
               std::string name_;

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

               //! Set debug message size
               void setDebug(uint32_t debug, std::string name);

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

               //! Accept a frame from master
               virtual void acceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );

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
               void acceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );

               //! Default accept frame call
               void defAcceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );
         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::stream::Slave> SlavePtr;
         typedef boost::shared_ptr<rogue::interfaces::stream::SlaveWrap> SlaveWrapPtr;
      }
   }
}
#endif

