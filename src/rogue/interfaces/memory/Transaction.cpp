/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Transaction
 * ----------------------------------------------------------------------------
 * File       : Transaction.cpp
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
#include <rogue/interfaces/memory/Transaction.h>
#include <rogue/interfaces/memory/TransactionLock.h>
#include <rogue/interfaces/memory/Master.h>
#include <rogue/interfaces/memory/Constants.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <rogue/GilRelease.h>
#include <rogue/ScopedGil.h>

namespace rim = rogue::interfaces::memory;
namespace bp  = boost::python;

// Init class counter
uint32_t rim::Transaction::classIdx_ = 0;

//! Class instance lock
boost::mutex rim::Transaction::classMtx_;

//! Create a master container
rim::TransactionPtr rim::Transaction::create () {
   rim::TransactionPtr m = boost::make_shared<rim::Transaction>();
   return(m);
}

void rim::Transaction::setup_python() {
   bp::class_<rim::Transaction, rim::TransactionPtr, boost::noncopyable>("Transaction",bp::no_init)
      .def("lock",    &rim::Transaction::lock)
      .def("id",      &rim::Transaction::id)
      .def("address", &rim::Transaction::address)
      .def("size",    &rim::Transaction::size)
      .def("type",    &rim::Transaction::type)
      .def("done",    &rim::Transaction::done)
      .def("expired", &rim::Transaction::expired)
      .def("setData", &rim::Transaction::setData)
      .def("getData", &rim::Transaction::getData)
   ;
}

//! Create object
rim::Transaction::Transaction() {
   endTime_.tv_sec    = 0;
   endTime_.tv_usec   = 0;
   startTime_.tv_sec  = 0;
   startTime_.tv_usec = 0;

   pyValid_ = false;

   iter_    = NULL;
   address_ = 0;
   size_    = 0;
   type_    = 0;
   error_   = 0;
   done_    = false;

   classMtx_.lock();
   if ( classIdx_ == 0 ) classIdx_ = 1;
   id_ = classIdx_;
   classIdx_++;
   classMtx_.unlock();
} 

//! Destroy object
rim::Transaction::~Transaction() { }

//! Get lock
rim::TransactionLockPtr rim::Transaction::lock() {
   return(rim::TransactionLock::create(shared_from_this()));
}

//! Get expired state
bool rim::Transaction::expired() { 
   return (iter_ == NULL); 
}

//! Get id
uint32_t rim::Transaction::id() { return id_; }

//! Get address
uint64_t rim::Transaction::address() { return address_; }

//! Get size
uint32_t rim::Transaction::size() { return size_; }

//! Get type
uint32_t rim::Transaction::type() { return type_; }

//! Complete transaction with passed error, lock must be held
void rim::Transaction::done(uint32_t error) {
   error_ = error;
   done_  = true;
   cond_.notify_all();
}

//! Wait for the transaction to complete
uint32_t rim::Transaction::wait() {
   struct timeval currTime;

   boost::unique_lock<boost::mutex> lock(lock_);

   while (! done_) {

      // Timeout?
      gettimeofday(&currTime,NULL);
      if ( endTime_.tv_sec  != 0 && endTime_.tv_usec != 0 && 
           timercmp(&currTime,&(endTime_),>) ) {

         done_  = true;
         error_ = rim::TimeoutError;
      }
      else cond_.timed_wait(lock,boost::posix_time::microseconds(1000));
   }

   // Reset
   if ( pyValid_ ) {
      rogue::ScopedGil gil;
      PyBuffer_Release(&(pyBuf_));
   }
   iter_    = NULL;
   pyValid_ = false;

   return (error_);
}

//! start iterator, caller must lock around access
rim::Transaction::iterator rim::Transaction::begin() {
   if ( iter_ == NULL ) throw(rogue::GeneralError("Transaction::begin","Invalid data"));
   return iter_;
}

//! end iterator, caller must lock around access
rim::Transaction::iterator rim::Transaction::end() {
   if ( iter_ == NULL ) throw(rogue::GeneralError("Transaction::end","Invalid data"));
   return iter_ + size_;
}

//! Set transaction data from python
void rim::Transaction::setData ( boost::python::object p, uint32_t offset ) {
   Py_buffer  pyBuf;
   uint8_t *  data;

   if ( PyObject_GetBuffer(p.ptr(),&pyBuf,PyBUF_CONTIG) < 0 )
      throw(rogue::GeneralError("Transaction::writePy","Python Buffer Error In Frame"));

   uint32_t count = pyBuf.len;

   if ( (offset + count) > size_ ) {
      PyBuffer_Release(&pyBuf);
      throw(rogue::GeneralError::boundary("Frame::write",offset+count,size_));
   }

   data = (uint8_t *)pyBuf.buf;
   std::copy(data,data+count,begin()+offset);
   PyBuffer_Release(&pyBuf);
}

//! Get transaction data from python
void rim::Transaction::getData ( boost::python::object p, uint32_t offset ) {
   Py_buffer  pyBuf;
   uint8_t *  data;

   if ( PyObject_GetBuffer(p.ptr(),&pyBuf,PyBUF_SIMPLE) < 0 ) 
      throw(rogue::GeneralError("Transaction::readPy","Python Buffer Error In Frame"));

   uint32_t count = pyBuf.len;

   if ( (offset + count) > size_ ) {
      PyBuffer_Release(&pyBuf);
      throw(rogue::GeneralError::boundary("Frame::readPy",offset+count,size_));
   }

   data = (uint8_t *)pyBuf.buf;
   std::copy(begin()+offset,begin()+offset+count,data);
   PyBuffer_Release(&pyBuf);
}

