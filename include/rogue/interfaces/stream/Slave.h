/**
 *-----------------------------------------------------------------------------
 * Title      : Stream interface slave
 * ----------------------------------------------------------------------------
 * File       : Slave.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-09-16
 * ----------------------------------------------------------------------------
 * Description:
 * Stream interface slave
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
         /** The stream slave accepts stream data from a master. It also
          * can accept frame allocation requests through its Pool base class.
          * A Slave object can be attached to multiple Master objects.
          */
         class Slave : public rogue::interfaces::stream::Pool {

               // Mutex
               boost::mutex mtx_;

               // Debug control
               uint32_t         debug_;
               boost::shared_ptr<rogue::Logging> log_;

               // Counters
               uint64_t frameCount_;
               uint64_t frameBytes_;

            public:

               //! Class factory which returns a pointer to a Slave (SlavePtr)
               /** Create a new Slave
                *
                * Not exposed to Python
                */
               static boost::shared_ptr<rogue::interfaces::stream::Slave> create ();

               //! Setup class for use in python
               /** Not exposed to Python
                */
               static void setup_python();

               //! Class creator
               /** Exposed as rogue.interfaces.stream.Slave() to Python
                */
               Slave();

               //! Destroy the object
               virtual ~Slave();

               //! Set debug message size
               /** This method enables debug messages when using the base Slave class
                * attached as a primary or secondar Slave on a Master. Typically used
                * when attaching a base Slave object for debug purposes.
                *
                * Exposed as setDebug() to Python
                * @param debug Maximum numer of bytes to print in debug message.
                * @param name Name to included in the debug messages.
                */
               void setDebug(uint32_t debug, std::string name);

               //! Accept a frame from master
               /** This method is called by the Master object to which this Slave is attached when
                * passing a Frame. By default this method will print debug information if enabled
                * and is typically re-implemented by a Slave sub-class.
                *
                * Re-implemented as _acceptFrame() in a Python subclass
                * @param frame Frame pointer (FramePtr)
                */
               virtual void acceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );

               //! Get frame counter
               /** Returns the total frames received. Only valid if acceptFrame is not re-implemented
                * as a sub-class. Typically used when attaching a base Slave object for debug purposes.
                *
                * Exposed as getFrameCount() to Python
                * @return Total number of Frame objects received.
                */
               uint64_t getFrameCount();

               //! Get byte counter
               /** Returns the total bytes received. Only valid if acceptFrame is not re-implemented
                * as a sub-class. Typically used when attaching a base Slave object for debug purposes.
                *
                * Exposed as getByteCount() to Python
                * @return Total number of bytes received.
                */
               uint64_t getByteCount();

         };

         //! Alias for using shared pointer as SlavePtr
         typedef boost::shared_ptr<rogue::interfaces::stream::Slave> SlavePtr;

#ifndef NO_PYTHON

         // Stream slave class, wrapper to enable pyton overload of virtual methods
         class SlaveWrap : 
            public rogue::interfaces::stream::Slave, 
            public boost::python::wrapper<rogue::interfaces::stream::Slave> {


            public:

               // Accept frame
               void acceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );

               // Default accept frame call
               void defAcceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );
         };

         typedef boost::shared_ptr<rogue::interfaces::stream::SlaveWrap> SlaveWrapPtr;
#endif

      }
   }
}
#endif

