/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Slave
 * ----------------------------------------------------------------------------
 * File       : Slave.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-09-20
 * Last update: 2016-09-20
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
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <rogue/GilRelease.h>
#include <rogue/ScopedGil.h>

namespace rim = rogue::interfaces::memory;
namespace bp = boost::python;

//! Create a slave container
rim::SlavePtr rim::Slave::create (uint32_t min, uint32_t max) {
   rim::SlavePtr s = boost::make_shared<rim::Slave>(min,max);
   return(s);
}

//! Create object
rim::Slave::Slave(uint32_t min, uint32_t max) { 
   min_ = min;
   max_ = max;
   enLocDone_ = false;
} 

//! Destroy object
rim::Slave::~Slave() { }

//! Enable local response
void rim::Slave::enLocDone(bool enable) {
   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);
   enLocDone_ = enable;
}

//! Register a master.
void rim::Slave::addMaster(uint32_t id, rim::MasterPtr master) {
   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);
   masterMap_[id] = master;
}

//! Get master device with index, called by sub classes
rim::MasterPtr rim::Slave::getMaster(uint32_t index) {
   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);

   if ( masterMap_.find(index) != masterMap_.end() ) return(masterMap_[index]);
   else throw(rogue::GeneralError("Slave::getMaster","Memory Master Not Linked To Slave"));
}

//! Return true if master is valid
bool rim::Slave::validMaster(uint32_t index) {
   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);
   if ( masterMap_.find(index) != masterMap_.end() ) return(true);
   else return(false);
}

//! Remove master from the list
void rim::Slave::delMaster(uint32_t index) {
   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);
   if ( masterMap_.find(index) != masterMap_.end() ) masterMap_.erase(index);
}

//! Return min access size to requesting master
uint32_t rim::Slave::doMinAccess() {
   return(min_);
}

//! Return max access size to requesting master
uint32_t rim::Slave::doMaxAccess() {
   return(max_);
}

//! Return offset
uint64_t rim::Slave::doOffset() {
   return(0);
}

//! Post a transaction
void rim::Slave::doTransaction(uint32_t id, rim::MasterPtr master, uint64_t address, uint32_t size, uint32_t type) {
   if ( enLocDone_ ) master->doneTransaction(id,0);
   else master->doneTransaction(id,rim::Unsupported);
}

void rim::Slave::setup_python() {
   bp::class_<rim::SlaveWrap, rim::SlaveWrapPtr, boost::noncopyable>("Slave",bp::init<uint32_t,uint32_t>())
      .def("create",         &rim::Slave::create)
      .staticmethod("create")
      .def("_addMaster",     &rim::Slave::addMaster)
      .def("_getMaster",     &rim::Slave::getMaster)
      .def("_validMaster",   &rim::Slave::validMaster)
      .def("_delMaster",     &rim::Slave::delMaster)
      .def("enLocDone",      &rim::Slave::enLocDone)
      .def("_doMinAccess",   &rim::Slave::doMinAccess,   &rim::SlaveWrap::defDoMinAccess)
      .def("_doMaxAccess",   &rim::Slave::doMaxAccess,   &rim::SlaveWrap::defDoMaxAccess)
      .def("_doOffset",      &rim::Slave::doOffset,      &rim::SlaveWrap::defDoOffset)
      .def("_doTransaction", &rim::Slave::doTransaction, &rim::SlaveWrap::defDoTransaction)
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
uint64_t rim::SlaveWrap::doOffset() {
   {
      rogue::ScopedGil gil;

      if (boost::python::override pb = this->get_override("_doOffset")) {
         try {
            return(pb());
         } catch (...) {
            PyErr_Print();
         }
      }
   }
   return(rim::Slave::doOffset());
}

//! Return offset
uint64_t rim::SlaveWrap::defDoOffset() {
   return(rim::Slave::doOffset());
}

//! Post a transaction. Master will call this method with the access attributes.
void rim::SlaveWrap::doTransaction(uint32_t id, rim::MasterPtr master,
                                   uint64_t address, uint32_t size, uint32_t type) {
   {
      rogue::ScopedGil gil;

      if (boost::python::override pb = this->get_override("_doTransaction")) {
         try {
            pb(id,master,address,size,type);
            return;
         } catch (...) {
            PyErr_Print();
         }
      }
   }
   rim::Slave::doTransaction(id,master,address,size,type);
}

//! Post a transaction. Master will call this method with the access attributes.
void rim::SlaveWrap::defDoTransaction(uint32_t id, rim::MasterPtr master,
                                      uint64_t address, uint32_t size, uint32_t type) {
   rim::Slave::doTransaction(id, master, address, size, type);
}

