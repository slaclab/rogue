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
   error_   = 0;

   sumTime_.tv_sec  = 1;
   sumTime_.tv_usec = 0;

   log_ = new Logging("memory.Master");
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

//! Reset transaction data, not python safe, needs lock
void rim::Master::rstTransaction(uint32_t id, uint32_t error, bool notify) {
   std::map<uint32_t, rogue::interfaces::memory::MasterTransaction>::iterator it;

   it = tran_.find(id);
   if ( it == tran_.end() ) {
      log_->info("Reset transaction failed to find transaction id=%i",id);
      return;
   }

   log_->debug("Resetting transaction id=%i",id);

   if ( it->second.pyValid ) PyBuffer_Release(&(it->second.pyBuf));

   tran_.erase(it);

   if ( error != 0 ) error_ = error;
   if ( notify ) cond_.notify_all();
}

//! Get transaaction count
uint32_t rim::Master::tranCount() {
   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);
   return(tran_.size());
}

//! Set slave
void rim::Master::setSlave ( rim::SlavePtr slave ) {
   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);
   slave_ = slave;
}

//! Get slave
rim::SlavePtr rim::Master::getSlave () {
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
   struct timeval currTime;
   rim::SlavePtr slave;
   uint32_t id;
   rim::MasterTransaction tran;

   {
      rogue::GilRelease noGil;
      boost::lock_guard<boost::mutex> lock(mtx_);
      slave = slave_;
      id    = genId();

      memset(&(tran.pyBuf),0,sizeof(Py_buffer));

      tran.pyValid = false;
      tran.tData   = (uint8_t *)data;
      tran.tSize   = size;

      tran.endTime.tv_sec = 0;
      tran.endTime.tv_usec = 0;
   
      tran_[id] = tran;
   }

   log_->debug("Request transaction type=%i id=%i",type,id);

   slave->doTransaction(id,shared_from_this(),address,size,type);

   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);

   gettimeofday(&currTime,NULL);
   timeradd(&currTime,&sumTime_,&(tran.endTime));

   tran_[id] = tran;
   return(id);
}

//! Post a transaction, called locally, forwarded to slave, python version
uint32_t rim::Master::reqTransactionPy(uint64_t address, boost::python::object p, uint32_t type) {
   struct timeval currTime;
   rim::SlavePtr slave;
   uint32_t id = 0;
   rim::MasterTransaction tran;

   {
      rogue::GilRelease noGil;
      boost::lock_guard<boost::mutex> lock(mtx_);
      slave = slave_;
      id    = genId();

      if ( PyObject_GetBuffer(p.ptr(),&(tran.pyBuf),PyBUF_SIMPLE) < 0 )
         throw(rogue::GeneralError("Master::reqTransactionPy","Python Buffer Error"));

      tran.pyValid = true;
      tran.tData   = (uint8_t *)tran.pyBuf.buf;
      tran.tSize   = tran.pyBuf.len;

      tran.endTime.tv_sec = 0;
      tran.endTime.tv_usec = 0;
   
      tran_[id] = tran;
   }
   log_->debug("Request transaction type=%i id=%i",type,id);
   slave->doTransaction(id,shared_from_this(),address,tran.tSize,type);

   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);

   gettimeofday(&currTime,NULL);
   timeradd(&currTime,&sumTime_,&(tran.endTime));

   tran_[id] = tran;
   return(id);
}

//! End current transaction, ensures data pointer is not update and de-allocates python buffer
void rim::Master::endTransaction(uint32_t id) {
   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);

   log_->debug("End transaction id=%i",id);

   if ( id == 0 ) {
      std::map<uint32_t, rogue::interfaces::memory::MasterTransaction>::iterator it;
      for ( it=tran_.begin(); it != tran_.end(); it++ ) rstTransaction(it->first,0,false);
   } else rstTransaction(id,0,false);
}

//! Transaction complete, set by slave, error passed
void rim::Master::doneTransaction(uint32_t id, uint32_t error) { 
   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);
   log_->debug("Done transaction id=%i",id);
   rstTransaction(id,error,true);
}

//! Set to master from slave, called by slave
void rim::Master::setTransactionData(uint32_t id, void *data, uint32_t offset, uint32_t size) { 
   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);

   std::map<uint32_t, rogue::interfaces::memory::MasterTransaction>::iterator it;

   it = tran_.find(id);
   if ( it == tran_.end() ) {
      log_->info("Set transaction data failed to find transaction id=%i",id);
      return;
   }

   if ( (offset + size) > it->second.tSize ) return;

   log_->debug("Set transaction data id=%i",id);
   memcpy(it->second.tData + offset, data, size);
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

   std::map<uint32_t, rogue::interfaces::memory::MasterTransaction>::iterator it;

   it = tran_.find(id);
   if ( it == tran_.end() ) {
      log_->info("Get transaction data failed to find transaction id=%i",id);
      return;
   }

   if ( (offset + size) > it->second.tSize ) return;

   log_->debug("Get transaction data id=%i",id);
   memcpy(data,it->second.tData + offset, size);
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
      .def("_tranCount",          &rim::Master::tranCount)
      .def("_reqMinAccess",       &rim::Master::reqMinAccess)
      .def("_reqMaxAccess",       &rim::Master::reqMaxAccess)
      .def("_reqAddress",         &rim::Master::reqAddress)
      .def("_getError",           &rim::Master::getError)
      .def("_setError",           &rim::Master::setError)
      .def("_setTimeout",         &rim::Master::setTimeout)
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
}

//! Transaction complete, called by slave when transaction is complete, error passed
void rim::MasterWrap::defDoneTransaction(uint32_t id, uint32_t error) {
   rim::Master::doneTransaction(id,error);
}

// Wait for transaction. Timeout in seconds
void rim::Master::waitTransaction(uint32_t id) {
   struct timeval currTime;

   std::map<uint32_t, rogue::interfaces::memory::MasterTransaction>::iterator it;

   rogue::GilRelease noGil;
   boost::unique_lock<boost::mutex> lock(mtx_);

   // No id means wait for all
   if ( id == 0 ) it = tran_.begin();
   else it = tran_.find(id);

   while (it != tran_.end()) {
      cond_.timed_wait(lock,boost::posix_time::microseconds(1000));

      // Timeout?
      if ( it->second.endTime.tv_sec != 0 && it->second.endTime.tv_usec != 0 ) {
         gettimeofday(&currTime,NULL);
         if ( timercmp(&currTime,&(it->second.endTime),>) ) {
            log_->info("Transaction timeout id=%i end=%i:%i curr=%i:%i",it->first,
                  it->second.endTime.tv_sec,it->second.endTime.tv_usec,currTime.tv_sec,currTime.tv_usec);
            rstTransaction(it->first,rim::TimeoutError,false);
            break;
         }
      }

      if ( id == 0 ) it = tran_.begin();
      else it = tran_.find(id);
   }
}

