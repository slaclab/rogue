/**
 *-----------------------------------------------------------------------------
 * Title      : Stream interface master
 * ----------------------------------------------------------------------------
 * File       : Master.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-08-08
 * Last update: 2016-08-08
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
#ifndef __INTERFACES_STREAM_MASTER_H__
#define __INTERFACES_STREAM_MASTER_H__
#include <stdint.h>
#include <stdio.h>
#include <pthread.h>
#include <string>
#include <vector>

#include <boost/python.hpp>

namespace interfaces {
   namespace stream {

   class Slave;
   class Frame;

      //! Stream master class
      /*
       * This class pushes frame data to a slave interface.
       */
      class Master {
            std::vector<boost::shared_ptr<interfaces::stream::Slave> > slaves_;

         public:

            //! Creator
            Master();

            //! Destructor
            virtual ~Master();

            //! Set frame slave
            void addSlave ( boost::shared_ptr<interfaces::stream::Slave> slave );

            //! Get frame from slave
            /*
             * An allocate command will be issued to each slave until one returns a buffer. 
             * If none return a buffer a null pointer will be returned.
             */
            boost::shared_ptr<interfaces::stream::Frame>
               reqFrame ( uint32_t size, bool zeroCopyEn);

            //! Push frame to slaves
            bool sendFrame ( boost::shared_ptr<interfaces::stream::Frame> frame );
      };

      // Convienence
      typedef boost::shared_ptr<interfaces::stream::Master> MasterPtr;
   }
}

#endif

