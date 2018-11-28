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

#include <boost/thread.hpp>
#include <rogue/interfaces/stream/Pool.h>
#include <rogue/Logging.h>

#ifndef NO_PYTHON
#include <boost/python.hpp>
#endif

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
         class Slave : public rogue::interfaces::stream::Pool {

               //! Mutex
               boost::mutex mtx_;

               //! Debug control
               uint32_t         debug_;
               rogue::LoggingPtr log_;

               //! Counters
               uint64_t frameCount_;
               uint64_t frameBytes_;

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

               //! Accept a frame from master
               virtual void acceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );

               //! Get frame counter
               uint64_t getFrameCount();

               //! Get byte counter
               uint64_t getByteCount();

         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::stream::Slave> SlavePtr;

#ifndef NO_PYTHON

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

         typedef boost::shared_ptr<rogue::interfaces::stream::SlaveWrap> SlaveWrapPtr;
#endif

      }
   }
}
#endif

