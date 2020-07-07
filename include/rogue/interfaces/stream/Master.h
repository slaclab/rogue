/**
 *-----------------------------------------------------------------------------
 * Title      : Stream interface master
 * ----------------------------------------------------------------------------
 * File       : Master.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-09-16
 * ----------------------------------------------------------------------------
 * Description:
 * Stream interface master
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
#ifndef __ROGUE_INTERFACES_STREAM_MASTER_H__
#define __ROGUE_INTERFACES_STREAM_MASTER_H__
#include <stdint.h>
#include <stdio.h>
#include <string>
#include <vector>
#include <thread>
#include <mutex>
#include <rogue/EnableSharedFromThis.h>

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
#endif

namespace rogue {
   namespace interfaces {
      namespace stream {

      class Slave;
      class Frame;

         //! Stream master class
         /** This class serves as the source for sending Frame data to a Slave. Each master
          * interfaces to one or more stream slave objects. The first stream Slave is used
          * to allocated new Frame objects and it is the last Slave to receive frame data.
          */
         class Master : public rogue::EnableSharedFromThis<rogue::interfaces::stream::Master> {

               // Vector of slaves
               std::vector<std::shared_ptr<rogue::interfaces::stream::Slave> > slaves_;

               // Slave mutex
               std::mutex slaveMtx_;

               // Default slave if not connected
               std::shared_ptr<rogue::interfaces::stream::Slave> defSlave_;

            public:

               //! Class factory which returns a pointer to a Master object (MasterPtr)
               /** Create a new Master
                *
                * Exposed as rogue.interfaces.stream.Master() to Python
                */
               static std::shared_ptr<rogue::interfaces::stream::Master> create ();

               // Setup class for use in python
               static void setup_python();

               // Class creator
               Master();

               // Destroy the object
               virtual ~Master();

               //! Get Slave Count
               /** Return the number of slaves.
                *
                * Exposed as _slaveCount() to Python.
                */
               uint32_t slaveCount ();

               //! Add a slave object
               /** Multiple slaves are allowed.
                * The first added slave is the Slave object from which the Master will request
                * new Frame allocations. The first Slave is also the last Slave object
                * which will receive the Frame.
                *
                * Exposed as _addSlave() to Python. Called in Python by the
                * pyrogue.streamTop() method.
                * @param slave Stream Slave pointer (SlavePtr)
                */
               void addSlave ( std::shared_ptr<rogue::interfaces::stream::Slave> slave );

               //! Request new Frame to be allocated by primary Slave
               /** This method is called to create a new Frame object. An empty Frame with
                * the requested payload capacity is create. The Master will forward this
                * request to the primary Slave object. The request for a new Frame includes
                * a flag which indicates if a zeroCopy frame is allowed. In most cases this
                * flag can be set to True. Non zero copy frames are requested if the Master may
                * need to transmit the same frame multiple times.
                *
                * Exposed as _reqFrame() to Python.
                * @param size Minimum size for requested Frame, larger Frame may be allocated
                * @param zeroCopyEn Flag which indicates if a zero copy mode Frame is allowed.
                * @return Newly allocated Frame pointer (FramePtr)
                */
               std::shared_ptr<rogue::interfaces::stream::Frame> reqFrame ( uint32_t size, bool zeroCopyEn);

               //! Push frame to all slaves
               /** This method sends the passed Frame to all of the attached Slave objects by
                * calling their acceptFrame() method. First the secondary Slaves are called in
                * order of attachment, followed last by the primary Slave. If the Frame is a
                * zero copy frame it will most likely be empty when the sendFrame() method returns.
                *
                * Exposed as _sendFrame to Python
                * @param frame Frame pointer (FramePtr) to send
                */
               void sendFrame ( std::shared_ptr<rogue::interfaces::stream::Frame> frame );

               //! Ensure frame is a single buffer
               /** This method makes sure the passed frame is composed of a single buffer.
                *  If the reqNew flag is true and the passed frame is not a single buffer, a
                *  new frame will be requested and the frame data will be copied, with the passed
                *  frame pointer being updated. The return value will indicate if the frame is a
                *  single buffer at the end of the process. A frame lock must be held when this
                *  method is called.
                *
                * Not exposed to Python
                * @param frame Reference to frame pointer (FramePtr)
                * @param rewEn Flag to determine if a new frame should be requested
                */
               bool ensureSingleBuffer ( std::shared_ptr<rogue::interfaces::stream::Frame> &frame, bool reqEn );

               //! Shut down any threads associated with this object
               /** This method is called to stop any frames from being generated by this Master and
                *  shut down any threads, allowing for a clean program exit
                *
                *  Exposed as stop() to Python
                *  Subclasses should override this method
                */
               virtual void stop();
    
#ifndef NO_PYTHON

               //! Support == operator in python
               void equalsPy ( boost::python::object p );

               //! Support >> operator in python
               boost::python::object rshiftPy ( boost::python::object p );

#endif

               //! Support == operator in C++
               void operator ==(std::shared_ptr<rogue::interfaces::stream::Slave> & other);

               //! Support >> operator in C++
               std::shared_ptr<rogue::interfaces::stream::Slave> &
                  operator >>(std::shared_ptr<rogue::interfaces::stream::Slave> & other);

         };

         //! Alias for using shared pointer as MasterPtr
         typedef std::shared_ptr<rogue::interfaces::stream::Master> MasterPtr;
      }
   }
}
#endif

