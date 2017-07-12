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

         //! Transaction tracker
         class MasterTransaction {
            public:

               //! Transaction start time
               struct timeval endTime;

               //! Transaction python buffer
               Py_buffer pyBuf;

               //! Python buffer is valid
               bool pyValid;

               //! Transaction data
               uint8_t * tData;

               //! Transaction size
               uint32_t tSize;

               //! Transaction id
               uint32_t tId;
         };

         //! Slave container
         class Master : public boost::enable_shared_from_this<rogue::interfaces::memory::Master> {

               //! Class instance counter
               static uint32_t classIdx_;

               //! Class instance lock
               static boost::mutex classIdxMtx_;

               //! Slave. Used for request forwards.
               boost::shared_ptr<rogue::interfaces::memory::Slave> slave_;

               //! Map of outstanding transactions
               std::map<uint32_t, rogue::interfaces::memory::MasterTransaction> tran_;

               //! Timeout value
               struct timeval sumTime_;

               //! Mutex
               boost::mutex mtx_;

               //! Conditional
               boost::condition_variable cond_;

               //! Transaction error
               uint32_t error_;

            protected:

               //! Generate a transaction id, not python safe
               static uint32_t genId();

               //! Reset transaction data
               void rstTransaction(uint32_t id, uint32_t error, bool notify);

            public:

               //! Create a master container
               static boost::shared_ptr<rogue::interfaces::memory::Master> create ();

               //! Setup class in python
               static void setup_python();

               //! Create object
               Master();

               //! Destroy object
               virtual ~Master();

               //! Get transaction count
               uint32_t tranCount();

               //! Set slave
               void setSlave ( boost::shared_ptr<rogue::interfaces::memory::Slave> slave );

               //! Get slave
               boost::shared_ptr<rogue::interfaces::memory::Slave> getSlave();

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
               void setTimeout(uint32_t timeout);

               //! Post a transaction, called locally, forwarded to slave, data pointer is optional
               uint32_t reqTransaction(uint64_t address, uint32_t size, void *data, uint32_t type);

               //! Post a transaction, called locally, forwarded to slave, python version
               uint32_t reqTransactionPy(uint64_t address, boost::python::object p, uint32_t type);

               //! End current transaction, ensures data pointer is not update and de-allocates python buffer
               void endTransaction(uint32_t id);

               //! Transaction complete, called by slave when transaction is complete, error passed
               virtual void doneTransaction(uint32_t id, uint32_t error);

               //! Set to master from slave, called by slave to push data into master.
               virtual void setTransactionData(uint32_t id, void *data, uint32_t offset, uint32_t size);

               //! Set to master from slave, called by slave to push data into master. Python Version.
               void setTransactionDataPy(uint32_t id, uint32_t offset, boost::python::object p);

               //! Get from master to slave, called by slave to pull data from mater.
               virtual void getTransactionData(uint32_t id, void *data, uint32_t offset, uint32_t size);

               //! Get from master to slave, called by slave to pull data from mater. Python Version.
               void getTransactionDataPy(uint32_t id, uint32_t offset, boost::python::object p);

               //! wait for done or timeout, if zero wait for all transactions
               void waitTransaction(uint32_t id);

         };

         //! Memory master class, wrapper to enable pyton overload of virtual methods
         class MasterWrap : 
            public rogue::interfaces::memory::Master,
            public boost::python::wrapper<rogue::interfaces::memory::Master> {

            public:

               //! Transaction complete, called by slave when transaction is complete, error passed
               void doneTransaction(uint32_t id, uint32_t error);

               //! Transaction complete, called by slave when transaction is complete, error passed
               void defDoneTransaction(uint32_t id, uint32_t error);
         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::memory::Master> MasterPtr;
         typedef boost::shared_ptr<rogue::interfaces::memory::MasterWrap> MasterWrapPtr;

      }
   }
}

#endif

