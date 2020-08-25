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
#include <memory>
#include <rogue/GilRelease.h>
#include <rogue/ScopedGil.h>

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

namespace rim = rogue::interfaces::memory;

// Init class counter
uint32_t rim::Slave::classIdx_ = 0;

//! Class instance lock
std::mutex rim::Slave::classMtx_;

//! Create a slave container
rim::SlavePtr rim::Slave::create (uint32_t min, uint32_t max) {
   rim::SlavePtr s = std::make_shared<rim::Slave>(min,max);
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

   name_ = std::string("Unnamed_") + std::to_string(id_);
}

//! Destroy object
rim::Slave::~Slave() { }


//! Stop the interface
void rim::Slave::stop() {}

//! Register a master.
void rim::Slave::addTransaction(rim::TransactionPtr tran) {
   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> lock(slaveMtx_);
   tranMap_[tran->id()] = tran;
}

//! Get transaction with index, called by sub classes
rim::TransactionPtr rim::Slave::getTransaction(uint32_t index) {
   rim::TransactionPtr ret;
   TransactionMap::iterator it;
   TransactionMap::iterator exp;

   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> lock(slaveMtx_);

   if ( (it = tranMap_.find(index)) != tranMap_.end() ) {
      ret = it->second;

      // Remove from list
      tranMap_.erase(it);

      // Update any timers for transactions started after received transaction
      exp = tranMap_.end();
      for ( it = tranMap_.begin(); it != tranMap_.end(); ++it ) {
         if ( it->second->expired() ) exp = it;
         else it->second->refreshTimer(ret);
      }

      // Clean up if we found an expired transaction, overtime this will clean up
      // the list, even if it deletes one expired transaction per call
      if ( exp != tranMap_.end() ) {
          tranMap_.erase(exp);
      }

   }
   return ret;
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

//! Get name from slave
std::string rim::Slave::name() {
   return name_;
}

//! Set name
void rim::Slave::setName(std::string name) {
   name_ = name;
}

//! Return id to requesting master
uint32_t rim::Slave::doSlaveId() {
   return(id());
}

//! Return name to requesting master
std::string rim::Slave::doSlaveName() {
   return(name());
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
   transaction->error("Unsupported transaction using unconnected memory bus");
}

void rim::Slave::setup_python() {
#ifndef NO_PYTHON
   bp::class_<rim::SlaveWrap, rim::SlaveWrapPtr, boost::noncopyable>("Slave",bp::init<uint32_t,uint32_t>())
      .def("setName",         &rim::Slave::setName)
      .def("_addTransaction", &rim::Slave::addTransaction)
      .def("_getTransaction", &rim::Slave::getTransaction)
      .def("_doMinAccess",    &rim::Slave::doMinAccess,   &rim::SlaveWrap::defDoMinAccess)
      .def("_doMaxAccess",    &rim::Slave::doMaxAccess,   &rim::SlaveWrap::defDoMaxAccess)
      .def("_doAddress",      &rim::Slave::doAddress,     &rim::SlaveWrap::defDoAddress)
      .def("_doTransaction",  &rim::Slave::doTransaction, &rim::SlaveWrap::defDoTransaction)
      .def("__lshift__",      &rim::Slave::lshiftPy)
      .def("_stop",           &rim::Slave::stop)
   ;
#endif
}

#ifndef NO_PYTHON

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

void rim::Slave::lshiftPy ( boost::python::object p ) {
   rim::MasterPtr mst;

   // First Attempt to access object as a memory master
   boost::python::extract<rim::MasterPtr> get_master(p);

   // Test extraction
   if ( get_master.check() ) mst = get_master();

   // Otherwise look for indirect call
   else if ( PyObject_HasAttrString(p.ptr(), "_getMemoryMaster" ) ) {

      // Attempt to convert returned object to master pointer
      boost::python::extract<rim::MasterPtr> get_master(p.attr("_getMemoryMaster")());

      // Test extraction
      if ( get_master.check() ) mst = get_master();
   }

   // Success
   if ( mst != NULL ) mst->setSlave(shared_from_this());
   else throw(rogue::GeneralError::create("memory::Slave::lshiftPy","Attempt to use << operator with incompatible memory master"));
}

#endif

//! Support << operator in C++
rim::MasterPtr & rim::Slave::operator <<(rim::MasterPtr & other) {
   other->setSlave(shared_from_this());
   return other;
}

