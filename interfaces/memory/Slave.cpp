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
#include <interfaces/memory/Slave.h>

namespace rim = rogue::interfaces::memory;

//! Create a slave container
rim::SlavePtr create () {
   rim::SlavePtr s = boost::make_shared<rim::Slave>() {
   return(s);
}

//! Create object
rim::Slave::Slave() { } 

//! Destroy object
rim::Slave::~Slave() { }

//! Issue a set of write transactions
bool rim::Slave::doWrite (BlockVector blocks) {
   return(false);
}

//! Issue a set of read transactions
bool rim::Slave::doRead  (BlockVector blocks) {
   return(false);
}

