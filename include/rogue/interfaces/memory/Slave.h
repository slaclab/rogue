/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Slave
 * ----------------------------------------------------------------------------
 * File       : Slave.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-09-20
 * Last update: 2016-09-20
 * ----------------------------------------------------------------------------
 * Description:
 * Memory slave interface.
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
#ifndef __ROGUE_INTERFACES_MEMORY_SLAVE_H__
#define __ROGUE_INTERFACES_MEMORY_SLAVE_H__
#include <stdint.h>
#include <vector>
#include <rogue/interfaces/memory/Master.h>
#include <boost/python.hpp>

namespace rogue {
   namespace interfaces {
      namespace memory {

         class Master;

         //! Slave container
         class Slave {

               //! Slave map
               std::map<uint32_t, boost::shared_ptr<rogue::interfaces::memory::Master> > masterMap_;

               //! Slave map lock
               boost::mutex masterMapMtx_;

            protected:

               //! Register a master.
               void addMaster(boost::shared_ptr<rogue::interfaces::memory::Master> master);

               //! Get master device with index
               boost::shared_ptr<rogue::interfaces::memory::Master> getMaster(uint32_t index);

               //! Return true if master is valid
               bool validMaster(uint32_t index);

            public:

               //! Create a slave container
               static boost::shared_ptr<rogue::interfaces::memory::Slave> create ();

               //! Setup class in python
               static void setup_python();

               //! Create object
               Slave();

               //! Destroy object
               ~Slave();

               //! Return min access size to requesting master
               virtual uint32_t doMinAccess();

               //! Post a transaction. Master will call this method with the access attributes.
               virtual void doTransaction(boost::shared_ptr<rogue::interfaces::memory::Master> master,
                                          uint64_t address, uint32_t size, bool write, bool posted);

         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::memory::Slave> SlavePtr;

      }
   }
}

#endif

