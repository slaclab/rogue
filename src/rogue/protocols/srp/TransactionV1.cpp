/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Register Protocol (SRP) Transaction V1
 * ----------------------------------------------------------------------------
 * File          : TransactionV1.cpp
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 09/17/2016
 * Last update   : 09/17/2016
 *-----------------------------------------------------------------------------
 * Description :
 *    Class to track a transaction
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
#include <rogue/protocols/srp/TransactionV1.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/memory/Block.h>
#include <boost/python.hpp>
#include <boost/thread.hpp>
#include <boost/make_shared.hpp>
#include <stdint.h>

namespace bp = boost::python;
namespace rps = rogue::protocols::srp;
namespace ris = rogue::interfaces::stream;
namespace rim = rogue::interfaces::memory;

//! Virtual init function
void rps::TransactionV1::init() {
   size_ = 0;
}

//! Generate request frame
bool rps::TransactionV1::intGenFrame(ris::FramePtr frame) {
   return(false);
}

//! Receive response frame
bool rps::TransactionV1::intRecvFrame(ris::FramePtr frame) {
   return(false);
}

//! Class creation
rps::TransactionV1Ptr rps::TransactionV1::create (bool write, rim::BlockPtr block) {
   rps::TransactionV1Ptr t = boost::make_shared<rps::TransactionV1>(write,block);
   return(t);
}

//! Setup class in python
void rps::TransactionV1::setup_python() {
   // Nothing to do
}

//! Creator with version constant
rps::TransactionV1::TransactionV1(bool write, rim::BlockPtr block) : Transaction(write,block) {
}

//! Deconstructor
rps::TransactionV1::~TransactionV1() { }

