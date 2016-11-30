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
#include <rogue/exceptions/GeneralException.h>
#include <boost/make_shared.hpp>
#include <rogue/common.h>

namespace rim = rogue::interfaces::memory;
namespace re  = rogue::exceptions;
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
} 

//! Destroy object
rim::Master::~Master() { }

//! Generate a transaction id, not python safe
void rim::Master::genId() {
   uint32_t nid;

   classIdxMtx_.lock();
   if ( classIdx_ == 0 ) classIdx_ = 1;
   nid = classIdx_;
   classIdx_++;
   classIdxMtx_.unlock();

   boost::lock_guard<boost::mutex> lock(tMtx_);
   tId_ = nid;
}

//! Get current transaction id, zero if no active transaction
uint32_t rim::Master::getId() {
   return(tId_);
}

//! Set slave
void rim::Master::setSlave ( rim::SlavePtr slave ) {
   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::lock_guard<boost::mutex> lock(slaveMtx_);
      slave_ = slave;
   }
   PyRogue_END_ALLOW_THREADS;
}

//! Get slave
rim::SlavePtr rim::Master::getSlave () {
   rim::SlavePtr ret;

   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::lock_guard<boost::mutex> lock(slaveMtx_);
      ret = slave_;
   }
   PyRogue_END_ALLOW_THREADS;

   return(ret);
}

//! Query the minimum access size in bytes for interface
uint32_t rim::Master::reqMinAccess() {
   rim::SlavePtr slave;

   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::lock_guard<boost::mutex> lock(slaveMtx_);
      slave = slave_;
   }
   PyRogue_END_ALLOW_THREADS;
   return(slave->doMinAccess());
}

//! Query the maximum access size in bytes for interface
uint32_t rim::Master::reqMaxAccess() {
   rim::SlavePtr slave;

   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::lock_guard<boost::mutex> lock(slaveMtx_);
      slave = slave_;
   }
   PyRogue_END_ALLOW_THREADS;
   return(slave->doMaxAccess());
}

//! Post a transaction, called locally, forwarded to slave
void rim::Master::reqTransaction(uint64_t address, uint32_t size, void *data, bool write, bool posted) {
   rim::SlavePtr slave;
   uint32_t id;

   PyRogue_BEGIN_ALLOW_THREADS;
   {
      genId();
      {
         boost::lock_guard<boost::mutex> lock(slaveMtx_);
         slave = slave_;
      }
      {
         boost::lock_guard<boost::mutex> lock(tMtx_);
         if ( pyValid_ ) PyBuffer_Release(&pyBuf_);
         tData_   = (uint8_t *)data;
         tSize_   = size;
         id       = tId_;
         pyValid_ = false;
      }
   }
   PyRogue_END_ALLOW_THREADS;
   slave->doTransaction(id,shared_from_this(),address,size,write,posted);
}

//! Post a transaction, called locally, forwarded to slave, python version
void rim::Master::reqTransactionPy(uint64_t address, boost::python::object p, bool write, bool posted) {
   rim::SlavePtr slave;
   uint32_t size;
   uint32_t id;

   PyRogue_BEGIN_ALLOW_THREADS;
   {

      genId();
      {
         boost::lock_guard<boost::mutex> lock(slaveMtx_);
         slave = slave_;
      }
      {
         boost::lock_guard<boost::mutex> lock(tMtx_);
         if ( pyValid_ ) PyBuffer_Release(&pyBuf_);

         if ( PyObject_GetBuffer(p.ptr(),&pyBuf_,PyBUF_SIMPLE) < 0 )
            throw(re::GeneralException("Master::reqTransactionPy","Python Buffer Error"));

         tData_   = (uint8_t *)pyBuf_.buf;
         tSize_   = pyBuf_.len;
         size     = pyBuf_.len;
         id       = tId_;
         pyValid_ = true;
      }
   }
   PyRogue_END_ALLOW_THREADS;
   slave->doTransaction(id,shared_from_this(),address,size,write,posted);
}

//! End current transaction, ensures data pointer is not update and de-allocates python buffer
void rim::Master::endTransaction() {
   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::lock_guard<boost::mutex> lock(tMtx_);

      if ( pyValid_ ) PyBuffer_Release(&pyBuf_);

      pyValid_ = false;
      tData_   = NULL;
      tSize_   = 0;
      tId_     = 0;
   }
   PyRogue_END_ALLOW_THREADS;
}

//! Transaction complete, set by slave, error passed
void rim::Master::doneTransaction(uint32_t id, uint32_t error) { 
   if ( id == tId_ ) endTransaction();
}

//! Set to master from slave, called by slave
void rim::Master::setTransactionData(uint32_t id, void *data, uint32_t offset, uint32_t size) { 
   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::lock_guard<boost::mutex> lock(tMtx_);

      if ( tId_ != id || tData_ == NULL || (offset + size) > tSize_ ) return;

      memcpy(tData_ + offset, data, size);
   }
   PyRogue_END_ALLOW_THREADS;
}

//! Set to master from slave, called by slave to push data into master. Python Version.
void rim::Master::setTransactionDataPy(uint32_t id, uint32_t offset, boost::python::object p) {
   Py_buffer pb;

   if ( PyObject_GetBuffer(p.ptr(),&pb,PyBUF_SIMPLE) < 0 )
      throw(re::GeneralException("Master::setTransactionDataPy","Python Buffer Error"));
   
   setTransactionData(id, pb.buf, offset, pb.len);
   PyBuffer_Release(&pb);
}

//! Get from master to slave, called by slave
void rim::Master::getTransactionData(uint32_t id, void *data, uint32_t offset, uint32_t size) { 
   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::lock_guard<boost::mutex> lock(tMtx_);

      if ( tId_ != id || tData_ == NULL || (offset + size) > tSize_ ) return;

      memcpy(data,tData_ + offset, size);
   }
   PyRogue_END_ALLOW_THREADS;
}

//! Get from master to slave, called by slave to pull data from mater. Python Version.
void rim::Master::getTransactionDataPy(uint32_t id, uint32_t offset, boost::python::object p) {
   Py_buffer pb;

   if ( PyObject_GetBuffer(p.ptr(),&pb,PyBUF_SIMPLE) < 0 )
      throw(re::GeneralException("Master::getTransactionDataPy","Python Buffer Error"));
   
   getTransactionData(id, pb.buf, offset, pb.len);
   PyBuffer_Release(&pb);
}

void rim::Master::setup_python() {
   bp::class_<rim::MasterWrap, rim::MasterWrapPtr, boost::noncopyable>("Master",bp::init<>())
      .def("_setSlave",           &rim::Master::setSlave)
      .def("_getSlave",           &rim::Master::getSlave)
      .def("_reqMinAccess",       &rim::Master::reqMinAccess)
      .def("_reqMaxAccess",       &rim::Master::reqMaxAccess)
      .def("_reqTransaction",     &rim::Master::reqTransactionPy)
      .def("_endTransaction",     &rim::Master::endTransaction)
      .def("_doneTransaction",    &rim::Master::doneTransaction, &rim::MasterWrap::defDoneTransaction)
      .def("_setTransactionData", &rim::Master::setTransactionDataPy)
      .def("_getTransactionData", &rim::Master::getTransactionDataPy)
   ;

   bp::register_ptr_to_python< boost::shared_ptr<rim::Master> >();
   bp::implicitly_convertible<rim::MasterWrapPtr, rim::MasterPtr>();
}

//! Transaction complete, called by slave when transaction is complete, error passed
void rim::MasterWrap::doneTransaction(uint32_t id, uint32_t error) {
   bool found;

   found = false;

   PyGILState_STATE pyState = PyGILState_Ensure();

   if (boost::python::override pb = this->get_override("_doneTransaction")) {
      found = true;
      try {
         pb(id,error);
      } catch (...) {
         PyErr_Print();
      }
   }
   PyGILState_Release(pyState);

   if ( ! found ) rim::Master::doneTransaction(id,error);
}

//! Transaction complete, called by slave when transaction is complete, error passed
void rim::MasterWrap::defDoneTransaction(uint32_t id, uint32_t error) {
   rim::Master::doneTransaction(id,error);
}

