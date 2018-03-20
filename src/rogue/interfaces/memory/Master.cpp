/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Master
 * ----------------------------------------------------------------------------
 * File       : Master.cpp
 * Created    : 2016-09-20
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
#include <rogue/interfaces/memory/Master.h>
#include <rogue/interfaces/memory/Slave.h>
#include <rogue/interfaces/memory/Constants.h>
#include <rogue/interfaces/memory/Transaction.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <rogue/GilRelease.h>
#include <rogue/ScopedGil.h>

namespace rim = rogue::interfaces::memory;
namespace bp  = boost::python;

//! Create a master container
rim::MasterPtr rim::Master::create () {
   rim::MasterPtr m = boost::make_shared<rim::Master>();
   return(m);
}

void rim::Master::setup_python() {
   bp::class_<rim::Master, rim::MasterPtr, boost::noncopyable>("Master",bp::init<>())
      .def("_setSlave",           &rim::Master::setSlave)
      .def("_getSlave",           &rim::Master::getSlave)
      .def("_reqSlaveId",         &rim::Master::reqSlaveId)
      .def("_reqMinAccess",       &rim::Master::reqMinAccess)
      .def("_reqMaxAccess",       &rim::Master::reqMaxAccess)
      .def("_reqAddress",         &rim::Master::reqAddress)
      .def("_getError",           &rim::Master::getError)
      .def("_setError",           &rim::Master::setError)
      .def("_setTimeout",         &rim::Master::setTimeout)
      .def("_reqTransaction",     &rim::Master::reqTransactionPy)
      .def("_waitTransaction",    &rim::Master::waitTransaction)
   ;
}

//! Create object
rim::Master::Master() {
   error_   = 0;
   slave_   = rim::Slave::create(4,4); // Empty placeholder

   sumTime_.tv_sec  = 1;
   sumTime_.tv_usec = 0;

   log_ = rogue::Logging::create("memory.Master");
} 

//! Destroy object
rim::Master::~Master() { }

//! Set slave
void rim::Master::setSlave ( rim::SlavePtr slave ) {
   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mastMtx_);
   slave_ = slave;
}

//! Get slave
rim::SlavePtr rim::Master::getSlave () {
   return(slave_);
}

//! Query the slave id
uint32_t rim::Master::reqSlaveId() {
   return(slave_->doSlaveId());
}

//! Query the minimum access size in bytes for interface
uint32_t rim::Master::reqMinAccess() {
   return(slave_->doMinAccess());
}

//! Query the maximum access size in bytes for interface
uint32_t rim::Master::reqMaxAccess() {
   return(slave_->doMaxAccess());
}

//! Query the offset
uint64_t rim::Master::reqAddress() {
   return(slave_->doAddress());
}

//! Get error
uint32_t rim::Master::getError() {
   return error_;
}

//! Rst error
void rim::Master::setError(uint32_t error) {
   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mastMtx_);
   error_ = error;
}

//! Set timeout
void rim::Master::setTimeout(uint64_t timeout) {
   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mastMtx_);

   if (timeout == 0 ) {
      sumTime_.tv_sec  = 1;
      sumTime_.tv_usec = 0;
   } else {
      sumTime_.tv_sec = (timeout / 1000000);
      sumTime_.tv_usec = (timeout % 1000000);
   }
}

//! Post a transaction, called locally, forwarded to slave
uint32_t rim::Master::reqTransaction(uint64_t address, uint32_t size, void *data, uint32_t type) {
   rim::TransactionPtr tran = rim::Transaction::create();

   tran->iter_    = (uint8_t *)data;
   tran->size_    = size;
   tran->address_ = address;
   tran->type_    = type;

   return(intTransaction(tran));
}

//! Post a transaction, called locally, forwarded to slave, python version
uint32_t rim::Master::reqTransactionPy(uint64_t address, boost::python::object p, uint32_t size, uint32_t offset, uint32_t type) {
   rim::TransactionPtr tran = rim::Transaction::create();

   if ( PyObject_GetBuffer(p.ptr(),&(tran->pyBuf_),PyBUF_SIMPLE) < 0 )
      throw(rogue::GeneralError("Master::reqTransactionPy","Python Buffer Error"));

   if ( size == 0 ) tran->size_ = tran->pyBuf_.len;
   else tran->size_ = size;

   if ( (tran->size_ + offset) > tran->pyBuf_.len ) {
      PyBuffer_Release(&(tran->pyBuf_));
      throw(rogue::GeneralError::boundary("Master::reqTransactionPy",(tran->size_+offset),tran->pyBuf_.len));
   }

   tran->pyValid_ = true;
   tran->iter_    = ((uint8_t *)tran->pyBuf_.buf) + offset;
   tran->type_    = type;
   tran->address_ = address;

   return(intTransaction(tran));
}

uint32_t rim::Master::intTransaction(rim::TransactionPtr tran) {
   TransactionMap::iterator it;
   struct timeval currTime;
   rim::SlavePtr slave;

   {
      rogue::GilRelease noGil;
      boost::lock_guard<boost::mutex> lock(mastMtx_);
      slave = slave_;

      gettimeofday(&(tran->startTime_),NULL);
      timeradd(&(tran->startTime_),&sumTime_,&(tran->endTime_));
      tranMap_[tran->id_] = tran;
   }

   log_->debug("Request transaction type=%i id=%i",tran->type_,tran->id_);
   slave->doTransaction(tran);
   return(tran->id_);
}

// Wait for transaction. Timeout in seconds
void rim::Master::waitTransaction(uint32_t id) {
   TransactionMap::iterator it;
   rim::TransactionPtr tran = NULL;
   uint32_t error;

   rogue::GilRelease noGil;
   while (1) {

      {  // Lock the vector
         boost::unique_lock<boost::mutex> lock(mastMtx_);
         if ( id != 0 ) it = tranMap_.find(id);
         else it = tranMap_.begin();

         if ( it != tranMap_.end() ) {
            tran = it->second;
            tranMap_.erase(it);
         }
         else break;
      }

      // Outside of lock
      if ( (error = tran->wait()) != 0 ) error_ = error;
   }
}

