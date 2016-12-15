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
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <rogue/common.h>

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
   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::lock_guard<boost::mutex> lock(mtx_);
      enLocDone_ = enable;
   }
   PyRogue_END_ALLOW_THREADS;
}

//! Register a master.
void rim::Slave::addMaster(uint32_t id, rim::MasterPtr master) {
   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::lock_guard<boost::mutex> lock(mtx_);
      masterMap_[id] = master;
   }
   PyRogue_END_ALLOW_THREADS;
}

//! Get master device with index, called by sub classes
rim::MasterPtr rim::Slave::getMaster(uint32_t index) {
   rim::MasterPtr ret;
   bool fail = false;

   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::lock_guard<boost::mutex> lock(mtx_);

      if ( masterMap_.find(index) != masterMap_.end() ) ret = masterMap_[index];
      else fail = true;
   }
   PyRogue_END_ALLOW_THREADS;

   if ( fail ) throw(rogue::GeneralError("Slave::getMaster","Memory Master Not Linked To Slave"));
   else return(ret);
}

//! Return true if master is valid
bool rim::Slave::validMaster(uint32_t index) {
   bool ret;

   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::lock_guard<boost::mutex> lock(mtx_);
      if ( masterMap_.find(index) != masterMap_.end() ) ret = true;
      else ret = false;
   }
   PyRogue_END_ALLOW_THREADS;
   return(ret);
}

//! Remove master from the list
void rim::Slave::delMaster(uint32_t index) {
   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::lock_guard<boost::mutex> lock(mtx_);
      if ( masterMap_.find(index) != masterMap_.end() ) masterMap_.erase(index);
   }
   PyRogue_END_ALLOW_THREADS;
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
void rim::Slave::doTransaction(uint32_t id, rim::MasterPtr master, uint64_t address, uint32_t size, bool write, bool posted) {
   if ( enLocDone_ ) master->doneTransaction(id,0);
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
   bool     found;
   uint32_t ret;

   found = false;
   ret = 0;

   PyGILState_STATE pyState = PyGILState_Ensure();

   if (boost::python::override pb = this->get_override("_doMinAccess")) {
      found = true;
      try {
         ret = pb();
      } catch (...) {
         PyErr_Print();
      }
   }
   PyGILState_Release(pyState);

   if ( ! found ) ret = rim::Slave::doMinAccess();
   return(ret);
}

//! Return min access size to requesting master
uint32_t rim::SlaveWrap::defDoMinAccess() {
   return(rim::Slave::doMinAccess());
}

//! Return max access size to requesting master
uint32_t rim::SlaveWrap::doMaxAccess() {
   bool     found;
   uint32_t ret;

   found = false;
   ret = 0;

   PyGILState_STATE pyState = PyGILState_Ensure();

   if (boost::python::override pb = this->get_override("_doMaxAccess")) {
      found = true;
      try {
         ret = pb();
      } catch (...) {
         PyErr_Print();
      }
   }
   PyGILState_Release(pyState);

   if ( ! found ) ret = rim::Slave::doMaxAccess();
   return(ret);
}

//! Return max access size to requesting master
uint32_t rim::SlaveWrap::defDoMaxAccess() {
   return(rim::Slave::doMinAccess());
}

//! Return offset
uint64_t rim::SlaveWrap::doOffset() {
   bool     found;
   uint64_t ret;

   found = false;
   ret = 0;

   PyGILState_STATE pyState = PyGILState_Ensure();

   if (boost::python::override pb = this->get_override("_doOffset")) {
      found = true;
      try {
         ret = pb();
      } catch (...) {
         PyErr_Print();
      }
   }
   PyGILState_Release(pyState);

   if ( ! found ) ret = rim::Slave::doOffset();
   return(ret);
}

//! Return offset
uint64_t rim::SlaveWrap::defDoOffset() {
   return(rim::Slave::doOffset());
}

//! Post a transaction. Master will call this method with the access attributes.
void rim::SlaveWrap::doTransaction(uint32_t id, rim::MasterPtr master,
                                   uint64_t address, uint32_t size, bool write, bool posted) {
   bool found;

   found = false;

   PyGILState_STATE pyState = PyGILState_Ensure();

   if (boost::python::override pb = this->get_override("_doTransaction")) {
      found = true;
      try {
         pb(id,master,address,size,write,posted);
      } catch (...) {
         PyErr_Print();
      }
   }
   PyGILState_Release(pyState);

   if ( ! found ) rim::Slave::doTransaction(id,master,address,size,write,posted);
}

//! Post a transaction. Master will call this method with the access attributes.
void rim::SlaveWrap::defDoTransaction(uint32_t id, rim::MasterPtr master,
                                      uint64_t address, uint32_t size, bool write, bool posted) {
   rim::Slave::doTransaction(id, master, address, size, write, posted);
}

