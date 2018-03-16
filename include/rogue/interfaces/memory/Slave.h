/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Slave
 * ----------------------------------------------------------------------------
 * File       : Slave.h
 * Created    : 2016-09-20
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
         class Transaction;

         //! Slave container
         class Slave {

               //! Class instance counter
               static uint32_t classIdx_;

               //! Class instance lock
               static boost::mutex classMtx_;

               //! Unique slave ID
               uint32_t id_;

               //! Alias for map
               typedef std::map<uint32_t, boost::weak_ptr<rogue::interfaces::memory::Transaction> > TransactionMap;

               //! Transaction map
               TransactionMap tranMap_;

               //! Slave lock
               boost::mutex slaveMtx_;

               //! Min access
               uint32_t min_;

               //! Max access
               uint32_t max_;

            public:

               //! Create a slave container
               static boost::shared_ptr<rogue::interfaces::memory::Slave> create (uint32_t min, uint32_t max);

               //! Setup class in python
               static void setup_python();

               //! Create object
               Slave(uint32_t min, uint32_t max);

               //! Destroy object
               virtual ~Slave();

               //! Register a transaction
               void addTransaction(boost::shared_ptr<rogue::interfaces::memory::Transaction> transaction);

               //! Get Transaction with index
               boost::shared_ptr<rogue::interfaces::memory::Transaction> getTransaction(uint32_t index);

               //! Remove transaction from the list, also cleanup stale transactions
               void delTransaction(uint32_t index);

               //! Get min size from slave
               uint32_t min();

               //! Get min size from slave
               uint32_t max();

               //! Get ID
               uint32_t id();

               //! Return ID to requesting master
               virtual uint32_t doSlaveId();

               //! Return min access size to requesting master
               virtual uint32_t doMinAccess();

               //! Return max access size to requesting master
               virtual uint32_t doMaxAccess();

               //! Return address
               virtual uint64_t doAddress();

               //! Post a transaction. Master will call this method with the access attributes.
               virtual void doTransaction(boost::shared_ptr<rogue::interfaces::memory::Transaction> transaction);
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
               uint64_t doAddress();

               //! Return offset
               uint64_t defDoAddress();

               //! Post a transaction. Master will call this method.
               void doTransaction(boost::shared_ptr<rogue::interfaces::memory::Transaction> transaction);

               //! Post a transaction. Master will call this method.
               void defDoTransaction(boost::shared_ptr<rogue::interfaces::memory::Transaction> transaction);

         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::memory::Slave> SlavePtr;
         typedef boost::shared_ptr<rogue::interfaces::memory::SlaveWrap> SlaveWrapPtr;

      }
   }
}

#endif

