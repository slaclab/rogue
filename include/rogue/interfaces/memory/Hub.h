/**
 *-----------------------------------------------------------------------------
 * Title      : Hub Hub
 * ----------------------------------------------------------------------------
 * File       : Hub.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-09-20
 * Last update: 2016-09-20
 * ----------------------------------------------------------------------------
 * Description:
 * A memory interface hub. Accepts requests from multiple masters and forwards
 * them to a downstream slave. Address is updated along the way. Includes support
 * for modification callbacks.
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
#ifndef __ROGUE_INTERFACES_MEMORY_HUB_H__
#define __ROGUE_INTERFACES_MEMORY_HUB_H__
#include <stdint.h>
#include <vector>

#include <rogue/interfaces/memory/Master.h>
#include <rogue/interfaces/memory/Slave.h>
#include <boost/python.hpp>
#include <boost/thread.hpp>

namespace rogue {
   namespace interfaces {
      namespace memory {

         //! Transaction container
         class Hub : public Master, public Slave {

            public:

               //! Create a block, class creator
               static boost::shared_ptr<rogue::interfaces::memory::Hub> create (uint64_t address);

               //! Setup class in python
               static void setup_python();

               //! Create a hub
               Hub(uint64_t address);

               //! Destroy a hub
               ~Hub();

               //! Return min access size to requesting master
               uint32_t doMinAccess();

               //! Return max access size to requesting master
               uint32_t doMaxAccess();

               //! Post a transaction. Master will call this method with the access attributes.
               void doTransaction(uint32_t id, boost::shared_ptr<rogue::interfaces::memory::Master> master,
                                  uint64_t address, uint32_t size, bool write, bool posted);

         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::memory::Hub> HubPtr;

      }
   }
}

#endif

