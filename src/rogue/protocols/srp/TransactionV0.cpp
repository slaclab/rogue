/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Register Protocol (SRP) Transaction V0
 * ----------------------------------------------------------------------------
 * File          : TransactionV0.cpp
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
#include <rogue/protocols/srp/TransactionV0.h>
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
void rps::TransactionV0::init() {

   if ((block_->getSize() % 4) != 0 || block_->getSize() < 4) {
      txSize_ = 0;
      rxSize_ = 0;
   }

   else {
      rxSize_ = (block_->getSize() + 12); // 2 x 32 bits for header, 1 x 32 for tail

      if (write_) txSize_ = rxSize_;
      else txSize_ = 16;
   }

   // First 32-bit value is context
   header_[0] = index_;

   // Second 32-bit value is address & mode
   header_[1] = (write_)?0x40000000:0x00000000;
   header_[1] |= (block_->getAddress() >> 2) & 0x3FFFFFFF;
}

//! Generate request frame
bool rps::TransactionV0::intGenFrame(ris::FramePtr frame) {
   uint32_t value;
   uint32_t cnt;
   uint32_t x;

   if ( (txSize_ == 0) || (frame->getAvailable() != txSize_) ) {
      block_->setError(1);
      return(false);
   }

   // Write header
   cnt  = frame->write(&(header_[0]),0,4);
   cnt += frame->write(&(header_[1]),cnt,4);

   // Write data
   if ( write_ ) {
      for (x=0; x < block_->getSize()/4; x++) {
         cnt += frame->write(block_->getData()+(x*4),cnt,4);
      }
   }

   // Read count
   else {
      value = (block_->getSize()/4)-1;
      cnt += frame->write(&value,cnt,4);
   }

   // Last field is zero
   value = 0;
   cnt += frame->write(&value,cnt,4);

   return(true);
}

//! Receive response frame
bool rps::TransactionV0::intRecvFrame(ris::FramePtr frame) {
   uint32_t rxHeader[2];
   uint32_t cnt;
   uint32_t tail;
   uint32_t x;

   if ( frame->getPayload() < rxSize_ ) return(false);

   // Get header fields
   cnt  = frame->read(&(rxHeader[0]),0,4);
   cnt += frame->read(&(rxHeader[1]),cnt,4);

   // Header mismatch
   if ( (rxHeader[0] != header_[0]) || (rxHeader[1] != header_[1])) return(false);

   // Read tail
   frame->read(&tail,frame->getPayload()-4,4);

   // Tail shows error
   if ( tail != 0 ) {
      block_->setError(tail);
      return(false);
   }

   // Copy payload if read
   if ( ! write_ ) {
      for (x=0; x < block_->getSize()/4; x++) {
         cnt += frame->read(block_->getData()+(x*4),cnt,4);
      }
   }

   block_->setStale(false);
   return(true); 
}

//! Class creation
rps::TransactionV0Ptr rps::TransactionV0::create (bool write, rim::BlockPtr block) {
   rps::TransactionV0Ptr t = boost::make_shared<rps::TransactionV0>(write,block);
   return(t);
}

//! Setup class in python
void rps::TransactionV0::setup_python() {
   // Nothing to do
}

//! Get transaction id
uint32_t rps::TransactionV0::extractTid (ris::FramePtr frame) {
   uint32_t tid;

   if ( frame->getPayload() < 16 ) return(0);

   frame->read(&tid,0,4);
   return(tid);
}

//! Creator with version constant
rps::TransactionV0::TransactionV0(bool write, rim::BlockPtr block) : Transaction(write,block) {
   // Nothing to do
}

//! Deconstructor
rps::TransactionV0::~TransactionV0() { 
   // Nothing to do
}

