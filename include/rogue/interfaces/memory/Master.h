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

               //! Transaction python buffer
               Py_buffer pyBuf_;

               //! Python buffer is valid
               bool pyValid_;

               //! Transaction data
               uint8_t * tData_;

               //! Transaction size
               uint32_t tSize_;

               //! Transaction lock
               boost::mutex tMtx_;

               //! Transaction id
               uint32_t tId_;

            protected:

               //! Generate a transaction id, not python safe
               void genId();

            public:

               //! Create a master container
               static boost::shared_ptr<rogue::interfaces::memory::Master> create ();

               //! Setup class in python
               static void setup_python();

               //! Create object
               Master();

               //! Destroy object
               ~Master();

               //! Get current transaction id, zero if no active transaction
               uint32_t getId();

               //! Set slave
               void setSlave ( boost::shared_ptr<rogue::interfaces::memory::Slave> slave );

               //! Get slave
               boost::shared_ptr<rogue::interfaces::memory::Slave> getSlave();

               //! Query the minimum access size in bytes for interface
               uint32_t reqMinAccess();

               //! Query the maximum transaction size in bytes for the interface
               uint32_t reqMaxAccess();

               //! Query the offset
               uint64_t reqOffset();

               //! Post a transaction, called locally, forwarded to slave, data pointer is optional
               void reqTransaction(uint64_t address, uint32_t size, void *data, bool write, bool posted);

               //! Post a transaction, called locally, forwarded to slave, python version
               void reqTransactionPy(uint64_t address, boost::python::object p, bool write, bool posted);

               //! End current transaction, ensures data pointer is not update and de-allocates python buffer
               void endTransaction();

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

