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
#include <boost/make_shared.hpp>
#include <rogue/common.h>

namespace rim = rogue::interfaces::memory;
namespace bp  = boost::python;

// Init class counter
uint32_t rim::Master::classIdx_ = 0;

//! Class instance lock
boost::mutex rim::Master::classIdxMtx_;

//! Create a master container
rim::MasterPtr rim::Master::create (uint64_t address, uint64_t size) {
   rim::MasterPtr m = boost::make_shared<rim::Master>(address, size);
   return(m);
}

//! Create object
rim::Master::Master(uint64_t address, uint64_t size) { 
   classIdxMtx_.lock();
   if ( classIdx_ == 0 ) classIdx_ = 1;
   index_ = classIdx_;
   classIdx_++;
   classIdxMtx_.unlock();
   slave_ = rim::Slave::create();
   address_  = address;
   size_     = size;
} 

//! Destroy object
rim::Master::~Master() { }

//! Get index
uint32_t rim::Master::getIndex() {
   return(index_);
}

//! Get size
uint64_t rim::Master::getSize() {
   return(size_);
}

//! Set size
void rim::Master::setSize(uint64_t size) {
   size_ = size;
}

//! Get address
uint64_t rim::Master::getAddress() {
   return(address_);
}

//! Set Address
void rim::Master::setAddress(uint64_t address) {
   address_ = address;
}

//! Inherit setting from master
void rim::Master::inheritFrom(rim::MasterPtr master ) {
   uint64_t mask;

   setSlave(master->getSlave());

   mask = (master->getSize() - 1);
   address_ &= mask;
   address_ |= master->getAddress();
}

//! Set slave, used for buffer request forwarding
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
void rim::Master::reqTransaction(bool write, bool posted) {
   rim::SlavePtr slave;

   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::lock_guard<boost::mutex> lock(slaveMtx_);
      slave = slave_;
   }
   PyRogue_END_ALLOW_THREADS;

   slave->doTransaction(shared_from_this(),address_,(size_&0xFFFFFFFF),write,posted);
}

//! Transaction complete, set by slave, error passed
void rim::Master::doneTransaction(uint32_t error) { }

//! Set to master from slave, called by slave
void rim::Master::setTransactionData(void *data, uint32_t offset, uint32_t size) { }

//! Get from master to slave, called by slave
void rim::Master::getTransactionData(void *data, uint32_t offset, uint32_t size) { }

void rim::Master::setup_python() {

   // slave can only exist as sub-class in python
   bp::class_<rim::Master, rim::MasterPtr, boost::noncopyable>("Master",bp::init<uint64_t,uint32_t>())
      .def("_setSlave",     &rim::Master::setSlave)
      .def("_getSlave",     &rim::Master::getSlave)
      .def("_reqMinAccess", &rim::Master::reqMinAccess)
      .def("_reqMaxAccess", &rim::Master::reqMaxAccess)
      .def("_setSize",      &rim::Master::setSize)
      .def("getSize",       &rim::Master::getSize)
      .def("getAddress",    &rim::Master::getAddress)
      .def("_setAddress",   &rim::Master::setAddress)
      .def("_inheritFrom",  &rim::Master::inheritFrom)
   ;

}

