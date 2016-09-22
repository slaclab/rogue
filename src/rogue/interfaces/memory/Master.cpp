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
#include <rogue/interfaces/memory/BlockVector.h>
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

//! Set primary slave, used for buffer request forwarding
void rim::Master::setSlave ( boost::shared_ptr<interfaces::memory::Slave> slave ) {
   slaveMtx_.lock();
   slave_ = slave;
   slaveMtx_.unlock();
}

//! Request a set of write transactions
bool rim::Master::reqWrite (rim::BlockVectorPtr blocks) {
   return(slave_->doWrite(blocks));
}

//! Request a single write transaction
bool rim::Master::reqWriteSingle (rim::BlockPtr block) {
   rim::BlockVectorPtr blocks = rim::BlockVector::create();
   blocks->append(block);
   return(slave_->doWrite(blocks));
}

//! Request a set of read transactions
bool rim::Master::reqRead (rim::BlockVectorPtr blocks) {
   return(slave_->doRead(blocks));
}

//! Request a single read transaction
bool rim::Master::reqReadSingle (rim::BlockPtr block) {
   rim::BlockVectorPtr blocks = rim::BlockVector::create();
   blocks->append(block);
   return(slave_->doRead(blocks));
}

void rim::Master::setup_python() {

   bp::class_<rim::Master, rim::MasterPtr, boost::noncopyable>("Master",bp::init<>())
      .def("create",         &rim::Master::create)
      .staticmethod("create")
      .def("setSlave",       &rim::Master::setSlave)
      .def("reqWrite",       &rim::Master::reqWrite)
      .def("reqWriteSingle", &rim::Master::reqWriteSingle)
      .def("reqRead",        &rim::Master::reqRead)
      .def("reqReadSingle",  &rim::Master::reqReadSingle)
   ;
}

