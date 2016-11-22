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
#include <rogue/interfaces/memory/DummySlave.h>
#include <rogue/interfaces/memory/Master.h>
#include <rogue/exceptions/GeneralException.h>
#include <boost/make_shared.hpp>

namespace rim = rogue::interfaces::memory;
namespace re  = rogue::exceptions;
namespace bp = boost::python;

//! Create object
rim::DummySlave::DummySlave() : rim::Slave() { } 

//! Destroy object
rim::DummySlave::~DummySlave() { }

//! Post a transaction
void rim::DummySlave::doTransaction(uint32_t id, rim::MasterPtr master, uint64_t address, uint32_t size, bool write, bool posted) {
   master->doneTransaction(id,0);
}

void rim::DummySlave::setup_python() {

   // slave can only exist as sub-class in python
   bp::class_<rim::DummySlave, rim::DummySlavePtr, boost::noncopyable>("DummySlave",bp::init<>());
}

