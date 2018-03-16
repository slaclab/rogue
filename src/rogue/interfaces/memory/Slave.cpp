/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Slave
 * ----------------------------------------------------------------------------
 * File       : Slave.cpp
 * Created    : 2016-09-20
 * ----------------------------------------------------------------------------
 * Description:
 * Memory slave interface.
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
#include <rogue/interfaces/memory/Slave.h>
#include <rogue/interfaces/memory/Master.h>
#include <rogue/interfaces/memory/Constants.h>
#include <rogue/interfaces/memory/Transaction.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <rogue/GilRelease.h>
#include <rogue/ScopedGil.h>

namespace rim = rogue::interfaces::memory;
namespace bp = boost::python;

// Init class counter
uint32_t rim::Slave::classIdx_ = 0;

//! Class instance lock
boost::mutex rim::Slave::classMtx_;

//! Create a slave container
rim::SlavePtr rim::Slave::create (uint32_t min, uint32_t max) {
   rim::SlavePtr s = boost::make_shared<rim::Slave>(min,max);
   return(s);
}

//! Create object
rim::Slave::Slave(uint32_t min, uint32_t max) { 
   min_ = min;
   max_ = max;

   classMtx_.lock();
   if ( classIdx_ == 0 ) classIdx_ = 1;
   id_ = classIdx_;
   classIdx_++;
   classMtx_.unlock();
} 

//! Destroy object
rim::Slave::~Slave() { }

//! Register a master.
void rim::Slave::addTransaction(rim::TransactionPtr tran) {
   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(slaveMtx_);
   tranMap_[tran->id()] = tran; // Weak pointer copy
}

//! Get transaction with index, called by sub classes
rim::TransactionPtr rim::Slave::getTransaction(uint32_t index) {
   rim::TransactionPtr ret;
   TransactionMap::iterator it;

   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(slaveMtx_);

   it = tranMap_.find(index);

   if ( ( it = tranMap_.find(index)) != tranMap_.end() ) {

      // Expired pointer
      if ( ! (ret = it->second.lock()) ) tranMap_.erase(it);
   } 
   return ret;
}

//! Remove master from the list
void rim::Slave::delTransaction(uint32_t index) {
   TransactionMap::iterator it;

   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(slaveMtx_);

   for (it = tranMap_.begin(); it != tranMap_.end(); ++it) {

      // Weak pointer or matching index
      if ( it->second.expired() || it->first == index ) tranMap_.erase(it);
   }
}

//! Get min size from slave
uint32_t rim::Slave::min() {
   return min_;
}

//! Get min size from slave
uint32_t rim::Slave::max() {
   return max_;
}

//! Get id from slave
uint32_t rim::Slave::id() {
   return id_;
}

//! Return id to requesting master
uint32_t rim::Slave::doSlaveId() {
   return(id());
}

//! Return min access size to requesting master
uint32_t rim::Slave::doMinAccess() {
   return(min());
}

//! Return max access size to requesting master
uint32_t rim::Slave::doMaxAccess() {
   return(max());
}

//! Return offset
uint64_t rim::Slave::doAddress() {
   return(0);
}

//! Post a transaction
void rim::Slave::doTransaction(rim::TransactionPtr transaction) {
   transaction->done(rim::Unsupported);
}

void rim::Slave::setup_python() {
   bp::class_<rim::SlaveWrap, rim::SlaveWrapPtr, boost::noncopyable>("Slave",bp::init<uint32_t,uint32_t>())
      .def("_addTransaction", &rim::Slave::addTransaction)
      .def("_getTransaction", &rim::Slave::getTransaction)
      .def("_delTransaction", &rim::Slave::delTransaction)
      .def("_doMinAccess",    &rim::Slave::doMinAccess,   &rim::SlaveWrap::defDoMinAccess)
      .def("_doMaxAccess",    &rim::Slave::doMaxAccess,   &rim::SlaveWrap::defDoMaxAccess)
      .def("_doAddress",      &rim::Slave::doAddress,     &rim::SlaveWrap::defDoAddress)
      .def("_doTransaction",  &rim::Slave::doTransaction, &rim::SlaveWrap::defDoTransaction)
   ;
}

//! Constructor
rim::SlaveWrap::SlaveWrap(uint32_t min, uint32_t max) : rim::Slave(min,max) {}

//! Return min access size to requesting master
uint32_t rim::SlaveWrap::doMinAccess() {
   {
      rogue::ScopedGil gil;

      if (boost::python::override pb = this->get_override("_doMinAccess")) {
         try {
            return(pb());
         } catch (...) {
            PyErr_Print();
         }
      }
   }
   return(rim::Slave::doMinAccess());
}

//! Return min access size to requesting master
uint32_t rim::SlaveWrap::defDoMinAccess() {
   return(rim::Slave::doMinAccess());
}

//! Return max access size to requesting master
uint32_t rim::SlaveWrap::doMaxAccess() {
   {
      rogue::ScopedGil gil;

      if (boost::python::override pb = this->get_override("_doMaxAccess")) {
         try {
            return(pb());
         } catch (...) {
            PyErr_Print();
         }
      }
   }
   return(rim::Slave::doMaxAccess());
}

//! Return max access size to requesting master
uint32_t rim::SlaveWrap::defDoMaxAccess() {
   return(rim::Slave::doMinAccess());
}

//! Return offset
uint64_t rim::SlaveWrap::doAddress() {
   {
      rogue::ScopedGil gil;

      if (boost::python::override pb = this->get_override("_doAddress")) {
         try {
            return(pb());
         } catch (...) {
            PyErr_Print();
         }
      }
   }
   return(rim::Slave::doAddress());
}

//! Return offset
uint64_t rim::SlaveWrap::defDoAddress() {
   return(rim::Slave::doAddress());
}

//! Post a transaction. Master will call this method with the access attributes.
void rim::SlaveWrap::doTransaction(rim::TransactionPtr transaction) {
   {
      rogue::ScopedGil gil;

      if (boost::python::override pb = this->get_override("_doTransaction")) {
         try {
            pb(transaction);
            return;
         } catch (...) {
            PyErr_Print();
         }
      }
   }
   rim::Slave::doTransaction(transaction);
}

//! Post a transaction. Master will call this method with the access attributes.
void rim::SlaveWrap::defDoTransaction(rim::TransactionPtr transaction) {
   rim::Slave::doTransaction(transaction);
}

