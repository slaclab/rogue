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
#include <rogue/interfaces/memory/Block.h>
#include <boost/make_shared.hpp>

namespace rim = rogue::interfaces::memory;
namespace bp  = boost::python;

//! Create a slave container
rim::MasterPtr rim::Master::create () {
   rim::MasterPtr m = boost::make_shared<rim::Master>();
   return(m);
}

//! Create object
rim::Master::Master() { 
   slave_ = rim::Slave::create();
} 

//! Destroy object
rim::Master::~Master() { }

//! Set slave, used for buffer request forwarding
void rim::Master::setSlave ( rim::SlavePtr slave ) {
   slaveMtx_.lock();
   slave_ = slave;
   slaveMtx_.unlock();
}

//! Get slave
rim::SlavePtr rim::Master::getSlave () {
   rim::SlavePtr p; 
   slaveMtx_.lock();
   p = slave_;
   slaveMtx_.unlock();
   return(p);
}

//! Post a transaction
void rim::Master::reqTransaction(bool write, bool posted, rim::BlockPtr block) {
   rim::SlavePtr p; 
   slaveMtx_.lock();
   p = slave_;
   slaveMtx_.unlock();
   p->doTransaction(write,posted,block);
}

void rim::Master::setup_python() {

   bp::class_<rim::Master, rim::MasterPtr, boost::noncopyable>("Master",bp::init<>())
      .def("create",         &rim::Master::create)
      .staticmethod("create")
      .def("setSlave",       &rim::Master::setSlave)
      .def("getSlave",       &rim::Master::getSlave)
      .def("reqTransaction", &rim::Master::reqTransaction)
   ;
}

