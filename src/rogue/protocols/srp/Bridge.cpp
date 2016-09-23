/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Register Protocol (SRP) Bridge
 * ----------------------------------------------------------------------------
 * File          : Bridge.cpp
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 09/17/2016
 * Last update   : 09/17/2016
 *-----------------------------------------------------------------------------
 * Description :
 *    SRP protocol bridge
 *-----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to 
 * the license terms in the LICENSE.txt file found in the top-level directory 
 * of this distribution and at: 
    * https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
 * No part of the rogue software platform, including this file, may be 
 * copied, modified, propagated, or distributed except according to the terms 
 * contained in the LICENSE.txt file.
 *-----------------------------------------------------------------------------
**/
#include <stdint.h>
#include <boost/thread.hpp>
#include <boost/make_shared.hpp>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/memory/Slave.h>
#include <rogue/interfaces/memory/Block.h>
#include <rogue/interfaces/memory/BlockVector.h>
#include <rogue/protocols/srp/Bridge.h>

namespace bp = boost::python;
namespace rps = rogue::protocols::srp;
namespace rim = rogue::interfaces::memory;
namespace ris = rogue::interfaces::stream;

//! Class creation
rps::BridgePtr rps::Bridge::create (uint32_t version) {
   rps::BridgePtr p = boost::make_shared<rps::Bridge>(version);
   return(p);
}

//! Setup class in python
void rps::Bridge::setup_python() {

   bp::class_<rps::Bridge, bp::bases<ris::Master,ris::Slave,rim::Slave>, 
              rps::BridgePtr, boost::noncopyable >("Bridge",bp::init<uint32_t>())
      .def("create",         &rps::Bridge::create)
      .staticmethod("create")
   ;

}

//! Creator with version constant
rps::Bridge::Bridge(uint32_t version) {
   version_ = version;
}

//! Deconstructor
rps::Bridge::~Bridge() {}

//! Issue a set of write transactions
bool rps::Bridge::doWrite (rim::BlockVectorPtr blocks) {

   return(false);
}

//! Issue a set of read transactions
bool rps::Bridge::doRead  (rim::BlockVectorPtr blocks) {


   return(false);
}

//! Accept a frame from master
bool rps::Bridge::acceptFrame ( ris::FramePtr frame, uint32_t timeout ) {



   return(false);
}


