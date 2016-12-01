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

               //! Min access
               uint32_t min_;

               //! Max access
               uint32_t max_;

            protected:

               //! Register a master.
               void addMaster(uint32_t index, boost::shared_ptr<rogue::interfaces::memory::Master> master);

               //! Get master device with index
               boost::shared_ptr<rogue::interfaces::memory::Master> getMaster(uint32_t index);

               //! Return true if master is valid
               bool validMaster(uint32_t index);

               //! Remove master from the list
               void delMaster(uint32_t index);

            public:

               //! Create a slave container
               static boost::shared_ptr<rogue::interfaces::memory::Slave> create (uint32_t min, uint32_t max);

               //! Setup class in python
               static void setup_python();

               //! Create object
               Slave(uint32_t min, uint32_t max);

               //! Destroy object
               ~Slave();

               //! Return min access size to requesting master
               virtual uint32_t doMinAccess();

               //! Return max access size to requesting master
               virtual uint32_t doMaxAccess();

               //! Return offset address
               virtual uint64_t doOffset();

               //! Post a transaction. Master will call this method with the access attributes.
               virtual void doTransaction(uint32_t id, boost::shared_ptr<rogue::interfaces::memory::Master> master,
                                          uint64_t address, uint32_t size, bool write, bool posted);

         };

         //! Memory slave class, wrapper to enable pyton overload of virtual methods
         class SlaveWrap : 
            public rogue::interfaces::memory::Slave, 
            public boost::python::wrapper<rogue::interfaces::memory::Slave> {

            public:

               //! Constructor
               SlaveWrap(uint32_t min, uint32_t max);

               //! Return min access size to requesting master
               uint32_t doMinAccess();

               //! Return min access size to requesting master
               uint32_t defDoMinAccess();

               //! Return max access size to requesting master
               uint32_t doMaxAccess();

               //! Return max access size to requesting master
               uint32_t defDoMaxAccess();

               //! Return offset
               uint64_t doOffset();

               //! Return offset
               uint64_t defDoOffset();

               //! Post a transaction. Master will call this method with the access attributes.
               void doTransaction(uint32_t id, boost::shared_ptr<rogue::interfaces::memory::Master> master,
                                  uint64_t address, uint32_t size, bool write, bool posted);

               //! Post a transaction. Master will call this method with the access attributes.
               void defDoTransaction(uint32_t id, boost::shared_ptr<rogue::interfaces::memory::Master> master,
                                     uint64_t address, uint32_t size, bool write, bool posted);

         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::memory::Slave> SlavePtr;
         typedef boost::shared_ptr<rogue::interfaces::memory::SlaveWrap> SlaveWrapPtr;

      }
   }
}

#endif

