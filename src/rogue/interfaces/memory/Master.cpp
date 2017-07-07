/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Master
 * ----------------------------------------------------------------------------
 * File       : Master.cpp
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
#include <rogue/interfaces/memory/Master.h>
#include <rogue/interfaces/memory/Slave.h>
#include <rogue/interfaces/memory/Constants.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <rogue/GilRelease.h>
#include <rogue/ScopedGil.h>

namespace rim = rogue::interfaces::memory;
namespace bp  = boost::python;

// Init class counter
uint32_t rim::Master::classIdx_ = 0;

//! Class instance lock
boost::mutex rim::Master::classIdxMtx_;

//! Create a master container
rim::MasterPtr rim::Master::create () {
   rim::MasterPtr m = boost::make_shared<rim::Master>();
   return(m);
}

//! Create object
rim::Master::Master() {
   slave_   = rim::Slave::create(4,4);
   pyValid_ = false;
   tData_   = NULL;
   tSize_   = 0;
   tId_     = 0;
   error_   = 0;
   timeout_ = 1000000;
} 

//! Destroy object
rim::Master::~Master() { }

//! Generate a transaction id, not python safe
uint32_t rim::Master::genId() {
   uint32_t nid;

   classIdxMtx_.lock();
   if ( classIdx_ == 0 ) classIdx_ = 1;
   nid = classIdx_;
   classIdx_++;
   classIdxMtx_.unlock();

   return(nid);
}

//! Get current transaction id, zero if no active transaction
uint32_t rim::Master::getId() {
   return(tId_);
}

//! Set slave
void rim::Master::setSlave ( rim::SlavePtr slave ) {
   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);
   slave_ = slave;
}

//! Get slave
rim::SlavePtr rim::Master::getSlave () {
   rim::SlavePtr ret;

   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);
   return(slave_);
}

//! Query the minimum access size in bytes for interface
uint32_t rim::Master::reqMinAccess() {
   rim::SlavePtr slave;

   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);
   slave = slave_;
   return(slave->doMinAccess());
}

//! Query the maximum access size in bytes for interface
uint32_t rim::Master::reqMaxAccess() {
   rim::SlavePtr slave;

   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);
   slave = slave_;
   return(slave->doMaxAccess());
}

//! Query the offset
uint64_t rim::Master::reqAddress() {
   rim::SlavePtr slave;

   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);
   slave = slave_;
   return(slave->doAddress());
}

//! Get error
uint32_t rim::Master::getError() {
   return error_;
}

//! Rst error
void rim::Master::setError(uint32_t error) {
   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);

   error_ = error;
}

//! Set timeout
void rim::Master::setTimeout(uint32_t timeout) {
   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);

   if (timeout == 0 ) timeout_ = 1;
   else timeout_ = timeout;
}

//! Get timeout
uint32_t rim::Master::getTimeout() {
   return timeout_;
}

//! Post a transaction, called locally, forwarded to slave
void rim::Master::reqTransaction(uint64_t address, uint32_t size, void *data, uint32_t type) {
   rim::SlavePtr slave;
   uint32_t id;

   {
      rogue::GilRelease noGil;
      boost::lock_guard<boost::mutex> lock(mtx_);
      slave = slave_;
      if ( pyValid_ ) PyBuffer_Release(&pyBuf_);
      tData_   = (uint8_t *)data;
      tSize_   = size;
      error_   = 0;
      tId_     = genId();
      id       = tId_;
      pyValid_ = false;
   }
   slave->doTransaction(id,shared_from_this(),address,size,type);

   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);
   gettimeofday(&tranTime_,NULL);
}

//! Post a transaction, called locally, forwarded to slave, python version
void rim::Master::reqTransactionPy(uint64_t address, boost::python::object p, uint32_t type) {
   rim::SlavePtr slave;
   uint32_t size = 0;
   uint32_t id = 0;

   {
      rogue::GilRelease noGil;
      boost::lock_guard<boost::mutex> lock(mtx_);
      slave = slave_;
      if ( pyValid_ ) PyBuffer_Release(&pyBuf_);

      if ( PyObject_GetBuffer(p.ptr(),&pyBuf_,PyBUF_SIMPLE) < 0 )
         throw(rogue::GeneralError("Master::reqTransactionPy","Python Buffer Error"));
      else {
         tData_   = (uint8_t *)pyBuf_.buf;
         tSize_   = pyBuf_.len;
         size     = pyBuf_.len;
         error_   = 0;
         tId_     = genId();
         id       = tId_;
         pyValid_ = true;
      }
   }
   slave->doTransaction(id,shared_from_this(),address,size,type);

   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);
   gettimeofday(&tranTime_,NULL);
}

//! Reset transaction data
void rim::Master::rstTransaction(uint32_t error, bool notify) {
   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);

   if ( pyValid_ ) PyBuffer_Release(&pyBuf_);

   pyValid_ = false;
   tData_   = NULL;
   tSize_   = 0;
   tId_     = 0;

   if ( error != 0 ) error_ = error;
   if ( notify ) cond_.notify_all();
}

//! End current transaction, ensures data pointer is not update and de-allocates python buffer
void rim::Master::endTransaction() {
   rstTransaction(0,false);
}

//! Transaction complete, set by slave, error passed
void rim::Master::doneTransaction(uint32_t id, uint32_t error) { 
   if ( id == tId_ ) rstTransaction(error,true);
}

//! Set to master from slave, called by slave
void rim::Master::setTransactionData(uint32_t id, void *data, uint32_t offset, uint32_t size) { 
   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);

   if ( tId_ != id || tData_ == NULL || (offset + size) > tSize_ ) return;

   memcpy(tData_ + offset, data, size);
}

//! Set to master from slave, called by slave to push data into master. Python Version.
void rim::Master::setTransactionDataPy(uint32_t id, uint32_t offset, boost::python::object p) {
   Py_buffer pb;

   if ( PyObject_GetBuffer(p.ptr(),&pb,PyBUF_SIMPLE) < 0 )
      throw(rogue::GeneralError("Master::setTransactionDataPy","Python Buffer Error"));
   
   setTransactionData(id, pb.buf, offset, pb.len);
   PyBuffer_Release(&pb);
}

//! Get from master to slave, called by slave
void rim::Master::getTransactionData(uint32_t id, void *data, uint32_t offset, uint32_t size) { 
   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);

   if ( tId_ != id || tData_ == NULL || (offset + size) > tSize_ ) return;

   memcpy(data,tData_ + offset, size);
}

//! Get from master to slave, called by slave to pull data from mater. Python Version.
void rim::Master::getTransactionDataPy(uint32_t id, uint32_t offset, boost::python::object p) {
   Py_buffer pb;

   if ( PyObject_GetBuffer(p.ptr(),&pb,PyBUF_SIMPLE) < 0 )
      throw(rogue::GeneralError("Master::getTransactionDataPy","Python Buffer Error"));
   
   getTransactionData(id, pb.buf, offset, pb.len);
   PyBuffer_Release(&pb);
}

void rim::Master::setup_python() {
   bp::class_<rim::MasterWrap, rim::MasterWrapPtr, boost::noncopyable>("Master",bp::init<>())
      .def("_setSlave",           &rim::Master::setSlave)
      .def("_getSlave",           &rim::Master::getSlave)
      .def("_getId",              &rim::Master::getId)
      .def("_reqMinAccess",       &rim::Master::reqMinAccess)
      .def("_reqMaxAccess",       &rim::Master::reqMaxAccess)
      .def("_reqAddress",         &rim::Master::reqAddress)
      .def("_getError",           &rim::Master::getError)
      .def("_setError",           &rim::Master::setError)
      .def("_setTimeout",         &rim::Master::setTimeout)
      .def("_getTimeout",         &rim::Master::getTimeout)
      .def("_reqTransaction",     &rim::Master::reqTransactionPy)
      .def("_endTransaction",     &rim::Master::endTransaction)
      .def("_doneTransaction",    &rim::Master::doneTransaction, &rim::MasterWrap::defDoneTransaction)
      .def("_setTransactionData", &rim::Master::setTransactionDataPy)
      .def("_getTransactionData", &rim::Master::getTransactionDataPy)
      .def("_waitTransaction",    &rim::Master::waitTransaction)
   ;

   bp::register_ptr_to_python< boost::shared_ptr<rim::Master> >();
   bp::implicitly_convertible<rim::MasterWrapPtr, rim::MasterPtr>();
}

//! Transaction complete, called by slave when transaction is complete, error passed
void rim::MasterWrap::doneTransaction(uint32_t id, uint32_t error) {
   if ( id != tId_ ) return;
   {
      rogue::ScopedGil gil;

      if (boost::python::override pb = this->get_override("_doneTransaction")) {
         try {
            pb(id,error);
         } catch (...) {
            PyErr_Print();
         }
      }
   }
   rstTransaction(error,true);
}

//! Transaction complete, called by slave when transaction is complete, error passed
void rim::MasterWrap::defDoneTransaction(uint32_t id, uint32_t error) {
   rim::Master::doneTransaction(id,error);
}

// Wait for transaction. Timeout in seconds
void rim::Master::waitTransaction() {

   // Return immediatly if transaction is done
   if ( tId_ == 0 ) return;

   struct timeval endTime;
   struct timeval sumTime;
   struct timeval currTime;

   sumTime.tv_sec = (timeout_ / 1000000);
   sumTime.tv_usec = (timeout_ % 1000000);
   timeradd(&tranTime_,&sumTime,&endTime);

   rogue::GilRelease noGil;
   boost::unique_lock<boost::mutex> lock(mtx_);

   while (tId_ > 0) {
      cond_.timed_wait(lock,boost::posix_time::microseconds(1000));

      // Timeout?S
      gettimeofday(&currTime,NULL);
      if ( timercmp(&currTime,&endTime,>) ) {
         lock.unlock();
         rstTransaction(rim::TimeoutError,false);
         break;
      }
   }
}

