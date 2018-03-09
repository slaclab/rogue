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
rim::TransactionPtr rim::Transaction::create (rim::MasterPtr master) {
   rim::TransactionPtr m = boost::make_shared<rim::Transaction>(master);
   return(m);
}

//! Create object
rim::Transaction::Transaction(rim::MasterPtr master) {
   master_ = master;

   endTime_.tv_sec    = 0;
   endTime_.tv_usec   = 0;
   startTime_.tv_sec  = 0;
   startTime_.tv_usec = 0;

   memset(pyBuf_),0,sizeof(Py_buffer);
   pyValid_ = false;

   data_    = NULL;
   address_ = 0;
   size_    = 0;
   type_    = 0;
   error_   = 0;

   classMtx_.lock();
   if ( classIdx_ == 0 ) classIdx_ = 1;
   id_ = classIdx_;
   classIdx_++;
   classMtx_.unlock();
} 

//! Destroy object
rim::Transaction::~Transaction() { }

//! Get id
uint32_t rim::Transaction::id() { return id_; }

//! Get address
uint32_t rim::Transaction::address(); { return address_; }

//! Get size
uint32_t rim::Transaction::size() { return size_; }

//! Get type
uint32_t rim::Transaction::type() { return type_; }

//! Complete transaction with passed error
void rim::Transaction::complete(uint32_t error) {
   {
      rogue::GilRelease noGil;
      boost::lock_guard<boost::mutex> lg(lock);
      error_ = error;
   }
   master_->doneTransaction(id_);
}

//! start iterator, caller must lock around access
rim::Transaction::iterator rim::Transaction::begin() {
   return data_;
}

//! end iterator, caller must lock around access
rim::Transaction::iterator rim::Transaction::end() {
   return data_ + size_;
}

//! Write data from python
void rim::Transaction::writePy ( boost::python::object p, uint32_t offset ) {
   Py_buffer  pyBuf;

   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lg(lock);
   noGil.acquire();

   if ( PyObject_GetBuffer(p.ptr(),&pyBuf,PyBUF_CONTIG) < 0 )
      throw(rogue::GeneralError("Transaction::writePy","Python Buffer Error In Frame"));

   uint32_t count = pyBuf.len;

   if ( (offset + count) > size_ ) {
      PyBuffer_Release(&pyBuf);
      throw(rogue::GeneralError::boundary("Frame::write",offset+count,size));
   }

   std::copy(pyBuf.buf,pyBuf.buf+count,data_+offset);
   PyBuffer_Release(&pyBuf);
}

//! Read data from python
void rim::Transaction::readPy ( boost::python::object p, uint32_t offset ) {
   Py_buffer  pyBuf;

   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lg(lock);
   noGil.acquire();

   if ( PyObject_GetBuffer(p.ptr(),&pyBuf,PyBUF_SIMPLE) < 0 ) 
      throw(rogue::GeneralError("Transaction::readPy","Python Buffer Error In Frame"));

   uint32_t count = pyBuf.len;

   if ( (offset + count) > size_ ) 
      PyBuffer_Release(&pyBuf);
      throw(rogue::GeneralError::boundary("Frame::readPy",offset+count,size));
   }

   std::copy(data_+offset,data_+offset+count,pyBuf.buf);
   PyBuffer_Release(&pyBuf);
}

