/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Register Protocol (SRP) Transaction
 * ----------------------------------------------------------------------------
 * File          : Transaction.cpp
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
#include <rogue/protocols/srp/Transaction.h>
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

// Init class counter
uint32_t rps::Transaction::tranIdx_ = 0;

//! Class instance lock
boost::mutex rps::Transaction::tranIdxMtx_;

//! Virtual init function
void rps::Transaction::init() {
   txSize_ = 0;
   rxSize_ = 0;
}

//! Generate request frame
bool rps::Transaction::intGenFrame(ris::FramePtr frame) {
   return(false);
}

//! Receive response frame
bool rps::Transaction::intRecvFrame(ris::FramePtr frame) {
   return(false);
}

//! Class creation
rps::TransactionPtr rps::Transaction::create (bool write, rim::BlockPtr block) {
   rps::TransactionPtr t = boost::make_shared<rps::Transaction>(write,block);
   return(t);
}

//! Setup class in python
void rps::Transaction::setup_python() {
   // Nothing to do
}

//! Get transaction id
uint32_t rps::Transaction::extractTid (ris::FramePtr frame) {
   return(0);
}

//! Creator with version constant
rps::Transaction::Transaction(bool write, rim::BlockPtr block) {
   tranIdxMtx_.lock();
   index_ = tranIdx_;
   tranIdx_++;
   tranIdxMtx_.unlock();
   block_ = block;
   write_ = write;
   init();
}

//! Deconstructor
rps::Transaction::~Transaction() { }

//! Get frame size
uint32_t rps::Transaction::getFrameSize() {
   return(txSize_);
}

//! Get transacton index
uint32_t rps::Transaction::getIndex() {
   return(index_);
}

//! Update frame with message data
bool rps::Transaction::genFrame(ris::FramePtr frame) {
   return(intGenFrame(frame));
}

//! Receive response frame
bool rps::Transaction::recvFrame(ris::FramePtr frame) {
   return(intRecvFrame(frame));
} 
