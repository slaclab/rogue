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

namespace rogue {
   namespace interfaces {
      namespace stream {

      class Slave;
      class Frame;

         //! Stream master class
         /** This class serves as the source for sending Frame data to a Slave. Each master
          * interfaces to a primary stream Slave and multiple secondar stream Slave ojects.
          * The primary stream Slave is used to allocated new Frame objects and it the
          * last Slave to receive frame data.
          */
         class Master {

               // Primary slave. Used for request forwards.
               std::shared_ptr<rogue::interfaces::stream::Slave> primary_;

               // Vector of slaves
               std::vector<std::shared_ptr<rogue::interfaces::stream::Slave> > slaves_;

               // Slave mutex
               std::mutex slaveMtx_;

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

               //! Set primary slave
               /** The primary slave is the Slave object from which the Master will request
                * new Frame allocations. The primary Slave is also the last Slave object
                * which will receive the Frame. Only one Slave can be set as Primary.
                *
                * Exposed as _setSlave() to Python. Called in Python by the
                * pyrogue.streamConnect() and pyrogue.streamConnectBiDir() methods.
                * @param slave Stream Slave pointer (SlavePtr)
                */
               void setSlave ( std::shared_ptr<rogue::interfaces::stream::Slave> slave );

               //! Add secondary slave
               /** Multiple secondary slaves are allowed.
                *
                * Exposed as _addSlave() to Python. Called in Python by the
                * pyrogue.streamTop() method.
                * @param slave Stream Slave pointer (SlavePtr)
                */
               void addSlave ( std::shared_ptr<rogue::interfaces::stream::Slave> slave );

               //! Request new Frame to be allocated by primary Slave
               /** This method is called to create a new Frame oject. An empty Frame with 
                * the requested payload capacity is create. The Master will forward this
                * request to the primary Slave oject. The request for a new Frame inclues
                * a flag which indicates if a zeroCopy frame is allowed. In most cases this
                * flag can be set to True. Non zero copy frames are requsted if the Master may
                * need to transmit the same frame multiple times.
                *
                * Exposed as _reqFrame() to Python.
                * @param size Minimum size for requsted Frame, larger Frame may be allocated
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
         };

         //! Alias for using shared pointer as MasterPtr
         typedef std::shared_ptr<rogue::interfaces::stream::Master> MasterPtr;
      }
   }
}
#endif

