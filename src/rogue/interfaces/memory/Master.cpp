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
#include <memory>
#include <rogue/GilRelease.h>
#include <rogue/ScopedGil.h>
#include <stdlib.h>

namespace rim = rogue::interfaces::memory;

#ifndef NO_PYTHON
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Create a master container
rim::MasterPtr rim::Master::create () {
   rim::MasterPtr m = std::make_shared<rim::Master>();
   return(m);
}

void rim::Master::setup_python() {
#ifndef NO_PYTHON
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
      .def("_copyBits",           &rim::Master::copyBits)
      .staticmethod("_copyBits")
      .def("_setBits",            &rim::Master::setBits)
      .staticmethod("_setBits")
      .def("_anyBits",            &rim::Master::anyBits)
      .staticmethod("_anyBits")
   ;
#endif
}

//! Create object
rim::Master::Master() {
   error_   = 0;
   slave_   = rim::Slave::create(4,4); // Empty placeholder

   rogue::defaultTimeout(sumTime_);

   log_ = rogue::Logging::create("memory.Master");
} 

//! Destroy object
rim::Master::~Master() { }

//! Set slave
void rim::Master::setSlave ( rim::SlavePtr slave ) {
   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> lock(mastMtx_);
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
   std::lock_guard<std::mutex> lock(mastMtx_);
   error_ = error;
}

//! Set timeout
void rim::Master::setTimeout(uint64_t timeout) {
   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> lock(mastMtx_);

   if (timeout != 0 ) {
      div_t divResult = div(timeout,1000000);
      sumTime_.tv_sec  = divResult.quot;
      sumTime_.tv_usec = divResult.rem;       
   }
}

//! Post a transaction, called locally, forwarded to slave
uint32_t rim::Master::reqTransaction(uint64_t address, uint32_t size, void *data, uint32_t type) {
   rim::TransactionPtr tran = rim::Transaction::create(sumTime_);

   tran->iter_    = (uint8_t *)data;
   tran->size_    = size;
   tran->address_ = address;
   tran->type_    = type;

   return(intTransaction(tran));
}

#ifndef NO_PYTHON

//! Post a transaction, called locally, forwarded to slave, python version
uint32_t rim::Master::reqTransactionPy(uint64_t address, boost::python::object p, uint32_t size, uint32_t offset, uint32_t type) {
   rim::TransactionPtr tran = rim::Transaction::create(sumTime_);

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

#endif

uint32_t rim::Master::intTransaction(rim::TransactionPtr tran) {
   TransactionMap::iterator it;
   struct timeval currTime;
   rim::SlavePtr slave;

   {
      rogue::GilRelease noGil;
      std::lock_guard<std::mutex> lock(mastMtx_);
      slave = slave_;
      tranMap_[tran->id_] = tran;
   }

   
   log_->debug("Request transaction type=%i id=%i",tran->type_,tran->id_);
   slave->doTransaction(tran);
   tran->refreshTimer(tran);
   return(tran->id_);
}

// Wait for transaction. Timeout in seconds
void rim::Master::waitTransaction(uint32_t id) {
   TransactionMap::iterator it;
   rim::TransactionPtr tran;
   uint32_t error;

   rogue::GilRelease noGil;
   while (1) {

      {  // Lock the vector
         std::unique_lock<std::mutex> lock(mastMtx_);
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

#ifndef NO_PYTHON

//! Copy bits from src to dst with lsbs and size
void rim::Master::copyBits(boost::python::object dst, uint32_t dstLsb, boost::python::object src, uint32_t srcLsb, uint32_t size) {

   Py_buffer srcBuf;
   Py_buffer dstBuf;
   uint32_t  srcBit;
   uint32_t  srcByte;
   uint8_t * srcData;
   uint32_t  dstBit;
   uint32_t  dstByte;
   uint8_t * dstData;
   uint32_t  rem;
   uint32_t  bytes;

   if ( PyObject_GetBuffer(dst.ptr(),&dstBuf,PyBUF_SIMPLE) < 0 )
      throw(rogue::GeneralError("Master::copyBits","Python Buffer Error"));

   if ( (dstLsb + size) > (dstBuf.len*8) ) {
      PyBuffer_Release(&dstBuf);
      throw(rogue::GeneralError::boundary("Master::copyBits",(dstLsb + size),(dstBuf.len*8)));
   }

   if ( PyObject_GetBuffer(src.ptr(),&srcBuf,PyBUF_SIMPLE) < 0 ) {
      PyBuffer_Release(&dstBuf);
      throw(rogue::GeneralError("Master::copyBits","Python Buffer Error"));
   }

   if ( (srcLsb + size) > (srcBuf.len*8) ) {
      PyBuffer_Release(&srcBuf);
      PyBuffer_Release(&dstBuf);
      throw(rogue::GeneralError::boundary("Master::copyBits",(srcLsb + size),(srcBuf.len*8)));
   }

   srcByte = srcLsb / 8;
   srcBit  = srcLsb % 8;
   srcData = (uint8_t *)srcBuf.buf;
   dstByte = dstLsb / 8;
   dstBit  = dstLsb % 8;
   dstData = (uint8_t *)dstBuf.buf;
   rem = size;

   do {
      bytes = rem / 8;

      // Aligned
      if ( (srcBit == 0) && (dstBit == 0) && (bytes > 0) ) {
         std::memcpy(&(dstData[dstByte]),&(srcData[srcByte]),bytes);
         dstByte += bytes;
         srcByte += bytes;
         rem -= (bytes * 8);
      }

      // Not aligned
      else {
         dstData[dstByte] &= ((0x1 << dstBit) ^ 0xFF);
         dstData[dstByte] |= ((srcData[srcByte] >> srcBit) & 0x1) << dstBit;
         srcByte += (++srcBit / 8);
         dstByte += (++dstBit / 8);
         srcBit %= 8;
         dstBit %= 8;
         rem -= 1;
      }
   } while (rem != 0);

   PyBuffer_Release(&srcBuf);
   PyBuffer_Release(&dstBuf);
}

//! Set all bits in dest with lbs and size
void rim::Master::setBits(boost::python::object dst, uint32_t lsb, uint32_t size) {
   Py_buffer dstBuf;
   uint32_t  dstBit;
   uint32_t  dstByte;
   uint8_t * dstData;
   uint32_t  rem;
   uint32_t  bytes;

   if ( PyObject_GetBuffer(dst.ptr(),&dstBuf,PyBUF_SIMPLE) < 0 )
      throw(rogue::GeneralError("Master::setBits","Python Buffer Error"));

   if ( (lsb + size) > (dstBuf.len*8) ) {
      PyBuffer_Release(&dstBuf);
      throw(rogue::GeneralError::boundary("Master::setBits",(lsb + size),(dstBuf.len*8)));
   }

   dstByte = lsb / 8;
   dstBit  = lsb % 8;
   dstData = (uint8_t *)dstBuf.buf;
   rem = size;

   do {
      bytes = rem / 8;

      // Aligned
      if ( (dstBit == 0) && (bytes > 0) ) {
         memset(&(dstData[dstByte]),0xFF,bytes);
         dstByte += bytes;
         rem -= (bytes * 8);
      }

      // Not aligned
      else {
         dstData[dstByte] |= (0x1 << dstBit);
         dstByte += (++dstBit / 8);
         dstBit %= 8;
         rem -= 1;
      }
   } while (rem != 0);

   PyBuffer_Release(&dstBuf);
}

//! Return true if any bits are set in range
bool rim::Master::anyBits(boost::python::object dst, uint32_t lsb, uint32_t size) {
   Py_buffer dstBuf;
   uint32_t  dstBit;
   uint32_t  dstByte;
   uint8_t * dstData;
   uint32_t  rem;
   uint32_t  bytes;
   bool      ret;

   if ( PyObject_GetBuffer(dst.ptr(),&dstBuf,PyBUF_SIMPLE) < 0 )
      throw(rogue::GeneralError("Master::anyBits","Python Buffer Error"));

   if ( (lsb + size) > (dstBuf.len*8) ) {
      PyBuffer_Release(&dstBuf);
      throw(rogue::GeneralError::boundary("Master::anyBits",(lsb + size),(dstBuf.len*8)));
   }

   dstByte = lsb / 8;
   dstBit  = lsb % 8;
   dstData = (uint8_t *)dstBuf.buf;
   rem = size;
   ret = false;

   do {
      bytes = rem / 8;

      // Aligned
      if ( (dstBit == 0) && (bytes > 0) ) {
         if (dstData[dstByte] != 0) ret = true;
         dstByte += 1;
         rem -= 8;
      }

      // Not aligned
      else {
         if ( (dstData[dstByte] & (0x1 << dstBit)) != 0) ret = true;
         dstByte += (++dstBit / 8);
         dstBit %= 8;
         rem -= 1;
      }
   } while (ret == false && rem != 0);

   PyBuffer_Release(&dstBuf);
   return ret;
}

#endif

