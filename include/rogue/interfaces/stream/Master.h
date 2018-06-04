/**
 *-----------------------------------------------------------------------------
 * Title      : Stream interface master
 * ----------------------------------------------------------------------------
 * File       : Master.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-09-16
 * Last update: 2016-09-16
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
#include <pthread.h>
#include <string>
#include <vector>
#include <boost/thread.hpp>

namespace rogue {
   namespace interfaces {
      namespace stream {

      class Slave;
      class Frame;

         //! Stream master class
         /*
          * This class pushes frame data to a slave interface.
          */
         class Master {

               //! Primary slave. Used for request forwards.
               boost::shared_ptr<rogue::interfaces::stream::Slave> primary_;

               //! Vector of slaves
               std::vector<boost::shared_ptr<rogue::interfaces::stream::Slave> > slaves_;

               //! Slave mutex
               boost::mutex slaveMtx_;

            public:

               //! Class creation
               static boost::shared_ptr<rogue::interfaces::stream::Master> create ();

               //! Setup class in python
               static void setup_python();

               //! Creator
               Master();

               //! Destructor
               virtual ~Master();

               //! Set primary slave, used for buffer request forwarding
               void setSlave ( boost::shared_ptr<rogue::interfaces::stream::Slave> slave );

               //! Add secondary slave
               void addSlave ( boost::shared_ptr<rogue::interfaces::stream::Slave> slave );

               //! Get frame from slave
               /*
                * An allocate command will be issued to the primary slave set with setSlave()
                * Pass size and flag indicating if zero copy buffers are allowed
                */
               boost::shared_ptr<rogue::interfaces::stream::Frame> reqFrame ( uint32_t size, bool zeroCopyEn);

               //! Push frame to all slaves
               void sendFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );
         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::stream::Master> MasterPtr;
      }
   }
}
#endif

