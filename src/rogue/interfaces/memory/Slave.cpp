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
#include <rogue/exceptions/GeneralException.h>
#include <boost/make_shared.hpp>

namespace rim = rogue::interfaces::memory;
namespace re  = rogue::exceptions;
namespace bp = boost::python;

//! Create a slave container
rim::SlavePtr rim::Slave::create () {
   rim::SlavePtr s = boost::make_shared<rim::Slave>();
   return(s);
}

//! Create object
rim::Slave::Slave() { } 

//! Destroy object
rim::Slave::~Slave() { }

//! Get master device with index, called by sub classes
rim::MasterPtr rim::Slave::getMaster(uint32_t index) {
   boost::lock_guard<boost::mutex> lock(masterMapMtx_);

   if ( masterMap_.find(index) != masterMap_.end() ) return(masterMap_[index]);
   else throw(re::GeneralException("Memory Master Not Linked To Slave"));
}

//! Return true if master is valid
bool rim::Slave::validMaster(uint32_t index) {
   boost::lock_guard<boost::mutex> lock(masterMapMtx_);
   if ( masterMap_.find(index) != masterMap_.end() ) return(true);
   else return(false);
}

//! Register a master. Called by Master class during addSlave.
void rim::Slave::addMaster(rim::MasterPtr master) {
   boost::lock_guard<boost::mutex> lock(masterMapMtx_);
   masterMap_[master->getIndex()] = master;
}

//! Post a transaction
void rim::Slave::doTransaction(rim::MasterPtr master, uint64_t address, uint32_t size, bool write, bool posted) {
   master->doneTransaction(0xFFFFFFFF);
}

void rim::Slave::setup_python() {

   // slave can only exist as sub-class in python
   bp::class_<rim::Slave, rim::SlavePtr, boost::noncopyable>("Slave",bp::init<>());
}

