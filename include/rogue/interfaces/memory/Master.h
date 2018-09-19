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
#include <boost/thread.hpp>
#include <rogue/Logging.h>

#ifndef NO_PYTHON
#include <boost/python.hpp>
#endif

namespace rogue {
   namespace interfaces {
      namespace memory {

         class Slave;
         class Transaction;

         //! Master container
         class Master {
            friend class Transaction;

            private:

               //! Alias for map
               typedef std::map<uint32_t, boost::shared_ptr<rogue::interfaces::memory::Transaction> > TransactionMap;

               //! Transaction map
               TransactionMap tranMap_;

               //! Slave. Used for request forwards.
               boost::shared_ptr<rogue::interfaces::memory::Slave> slave_;

               //! Timeout value
               struct timeval sumTime_;

               //! Mutex
               boost::mutex mastMtx_;

               //! Error status
               uint32_t error_;

               //! Log
               rogue::LoggingPtr log_;

            public:

               //! Create a master container
               static boost::shared_ptr<rogue::interfaces::memory::Master> create ();

               //! Setup class in python
               static void setup_python();

               //! Create object
               Master();

               //! Destroy object
               virtual ~Master();

               //! Set slave
               void setSlave ( boost::shared_ptr<rogue::interfaces::memory::Slave> slave );

               //! Get slave
               boost::shared_ptr<rogue::interfaces::memory::Slave> getSlave();

               //! Query the slave ID
               uint32_t reqSlaveId();

               //! Query the minimum access size in bytes for interface
               uint32_t reqMinAccess();

               //! Query the maximum transaction size in bytes for the interface
               uint32_t reqMaxAccess();

               //! Query the address
               uint64_t reqAddress();

               //! Get error
               uint32_t getError();

               //! Rst error
               void setError(uint32_t error);

               //! Set timeout
               void setTimeout(uint64_t timeout);

               //! Post a transaction, called locally, forwarded to slave, data pointer is optional
               uint32_t reqTransaction(uint64_t address, uint32_t size, void *data, uint32_t type);

#ifndef NO_PYTHON

               //! Post a transaction, called locally, forwarded to slave, python version
               // size and offset are optional to use a slice within the python buffer
               uint32_t reqTransactionPy(uint64_t address, boost::python::object p, uint32_t size, uint32_t offset, uint32_t type);

               //! Copy bits from src to dst with lsbs and size
               static void copyBits(boost::python::object dst, uint32_t dstLsb, boost::python::object src, uint32_t srcLsb, uint32_t size);

               //! Set all bits in dest with lbs and size
               static void setBits(boost::python::object dst, uint32_t lsb, uint32_t size);

#endif

            protected:

               //! Internal transaction
               uint32_t intTransaction(boost::shared_ptr<rogue::interfaces::memory::Transaction> tran);

            public:

               //! wait for done or timeout, if zero wait for all transactions
               void waitTransaction(uint32_t id);
         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::memory::Master> MasterPtr;
      }
   }
}

#endif

