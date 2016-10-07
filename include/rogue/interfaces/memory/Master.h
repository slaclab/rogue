/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Master
 * ----------------------------------------------------------------------------
 * File       : Master.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-09-20
 * Last update: 2016-09-20
 * ----------------------------------------------------------------------------
 * Description:
 * Memory master interface.
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
#ifndef __ROGUE_INTERFACES_MEMORY_MASTER_H__
#define __ROGUE_INTERFACES_MEMORY_MASTER_H__
#include <stdint.h>
#include <vector>
#include <boost/enable_shared_from_this.hpp>
#include <boost/python.hpp>
#include <boost/thread.hpp>

namespace rogue {
   namespace interfaces {
      namespace memory {

         class Slave;

         //! Slave container
         class Master : public boost::enable_shared_from_this<rogue::interfaces::memory::Master> {

               //! Class instance counter
               static uint32_t classIdx_;

               //! Class instance lock
               static boost::mutex classIdxMtx_;

               //! Slave. Used for request forwards.
               boost::shared_ptr<rogue::interfaces::memory::Slave> slave_;

               //! Slave mutex
               boost::mutex slaveMtx_;

               //! Index
               uint32_t index_;

            protected:

               //! Address
               uint64_t address_;

               //! Size tracking for transaction and/or managed space
               uint64_t size_;

               //! Get slave
               boost::shared_ptr<rogue::interfaces::memory::Slave> getSlave();

               //! Query the minimum access size in bytes for interface
               uint32_t reqMinAccess();

               //! Query the maximum transaction size in bytes for the interface
               uint32_t reqMaxAccess();

               //! Post a transaction, called locally, forwarded to slave
               void reqTransaction(bool write, bool posted);

            public:

               //! Create a master container
               static boost::shared_ptr<rogue::interfaces::memory::Master> create (uint64_t address, uint64_t size);

               //! Setup class in python
               static void setup_python();

               //! Get index
               uint32_t getIndex();

               //! Get size
               uint64_t getSize();

               //! Set size
               void setSize(uint64_t size);

               //! Get address
               uint64_t getAddress();

               //! Set address
               void setAddress(uint64_t address);

               //! Inherit settings from master
               /*
                * Updates local information based upon parent master
                */
               void inheritFrom(boost::shared_ptr<rogue::interfaces::memory::Master> parent );

               //! Create object
               Master(uint64_t address, uint64_t size);

               //! Destroy object
               ~Master();

               //! Set slave, used for memory access requests
               void setSlave ( boost::shared_ptr<rogue::interfaces::memory::Slave> slave );

               //! Transaction complete, called by slave when transaction is complete, error passed
               virtual void doneTransaction(uint32_t error);

               //! Set to master from slave, called by slave to push data into master.
               virtual void setTransactionData(void *data, uint32_t offset, uint32_t size);

               //! Get from master to slave, called by slave to pull data from mater.
               virtual void getTransactionData(void *data, uint32_t offset, uint32_t size);

         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::memory::Master> MasterPtr;

      }
   }
}

#endif

