/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue as a library base class
 * ----------------------------------------------------------------------------
 * File       : LibraryBase.cpp
 * ----------------------------------------------------------------------------
 * Description:
 * Base class for creating a Rogue shared library
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

#include <rogue/LibraryBase.h>
#include <stdint.h>
#include <vector>
#include <map>
#include <string>

namespace ris  = rogue::interfaces::stream;
namespace rim  = rogue::interfaces::memory;

rogue::LibraryBasePtr rogue::LibraryBase::create() {
   rogue::LibraryBasePtr ret = std::make_shared<rogue::LibraryBase>();
   return(ret);
}

rogue::LibraryBase::LibraryBase () {


}

rogue::LibraryBase::~LibraryBase() {
}

//! Add master stream
void rogue::LibraryBase::addMasterStream (std::string name, ris::MasterPtr mast) {
   _mastStreams[name] = mast;
}

//! Add slave stream
void rogue::LibraryBase::addSlaveStream (std::string name, ris::SlavePtr slave) {
   _slaveStreams[name] = slave;
}

//! Get master stream by name
ris::MasterPtr rogue::LibraryBase::getMasterStream(std::string name) {
   return _mastStreams[name];
}

//! Get slave stream by name
ris::SlavePtr rogue::LibraryBase::getSlaveStream(std::string name) {
   return _slaveStreams[name];
}

//! Get variable by name
rim::VariablePtr rogue::LibraryBase::getVariable(std::string name) {
   return _variables[name];
}

