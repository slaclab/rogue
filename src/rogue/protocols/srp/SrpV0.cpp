/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Register Protocol (SRP) SrpV0
 * ----------------------------------------------------------------------------
 * File          : SrpV0.cpp
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 09/17/2016
 * Last update   : 09/17/2016
 *-----------------------------------------------------------------------------
 * Description :
 *    SRP protocol bridge, Version 0
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
#include <rogue/interfaces/stream/FrameIterator.h>
#include <rogue/interfaces/memory/Slave.h>
#include <rogue/interfaces/memory/Constants.h>
#include <rogue/interfaces/memory/Transaction.h>
#include <rogue/protocols/srp/SrpV0.h>
#include <rogue/Logging.h>

namespace bp = boost::python;
namespace rps = rogue::protocols::srp;
namespace rim = rogue::interfaces::memory;
namespace ris = rogue::interfaces::stream;

//! Class creation
rps::SrpV0Ptr rps::SrpV0::create () {
   rps::SrpV0Ptr p = boost::make_shared<rps::SrpV0>();
   return(p);
}

//! Setup class in python
void rps::SrpV0::setup_python() {

   bp::class_<rps::SrpV0, rps::SrpV0Ptr, bp::bases<ris::Master,ris::Slave,rim::Slave>, boost::noncopyable >("SrpV0",bp::init<>());

}

//! Creator with version constant
rps::SrpV0::SrpV0() : ris::Master(), ris::Slave(), rim::Slave(4,2048) { 
   log_ = rogue::Logging::create("SrpV0");
}

//! Deconstructor
rps::SrpV0::~SrpV0() {}

//! Post a transaction
void rps::SrpV0::doTransaction(rim::TransactionPtr tran) {
   ris::Frame::iterator fIter;
   rim::Transaction::iterator tIter;
   ris::FramePtr  frame;
   uint32_t frameSize;
   uint32_t header[2];
   uint32_t rdLength[1];
   uint32_t tail[1];

   // Size error
   if ((tran->address() % min_) != 0 ) {
      master->doneTransaction(id,rim::AddressError);
      return;
   }

   // Size error
   if ((tran->size() % min_) != 0 || tran->size() < min_ || tran->size() > max_) {
      tran->done(rim::SizeError);
      return;
   }

   // Common header fields
   header[0]   = tran->id();
   header[1]   = (address >> 2) & 0x3FFFFFFF;
   rdLength[0] = (tran->size()/4)-1;
   tail[0]     = 0;

   // Build header for write
   if (type == rim::Write || type == rim::Post) {
      header[1] |= 0x40000000;
      frameSize = (size + sizeof(header) + sizeof(tail));
   } 
   else frameSize = sizeof(header) + sizeof(tail) + sizeof(rdLength); // One data entry

   // Request frame
   frame = reqFrame(frameSize,true);
   fIter = frame->begin();
   tIter = tran->begin();

   // Write header
   //std::copy(header,header+sizeof(header),fIter);
   fIter += sizeof(header);

   // Write data
   if ( type == rim::Write || type == rim::Post ) {
      //std::copy(tIter,tIter+tran->size(),fIter);
      fIter += tran->size();
   }

   // Read data
   else {
      //std::copy(rdLength,rdLength+sizeof(rdLength),fIter);
      fIter += sizeof(rdLength);
   }

   // Last field is zero
   //std::copy(tail,tail+sizeof(tail),fIter);

   if ( type == rim::Post ) tran->done(0);
   else addTransaction(tran);

   log_->debug("Send frame for id=0x%08x, addr 0x%08x. Size=%i, type=%i",tran->id(),tran->address(),tran->size(),tran->type());
   sendFrame(frame);
}

//! Accept a frame from master
void rps::SrpV0::acceptFrame ( ris::FramePtr frame ) {
   ris::Frame::iterator fIter;
   rim::Transaction::iterator tIter;
   rim::TransactionPtr tran;
   uint32_t header[2];
   uint32_t tail[1];
   uint32_t  id;
   //uint32_t  size;
   //uint32_t  cnt;
   //uint32_t  temp;

   // Check frame size
   if ( frame->getPayload() < 16 ) return; // Invalid frame, drop it

   // Get the header
   std::copy(fIter,fIter+sizeof(header),header);

   // Extract id from frame
   if = header[0];
   log_->debug("Recv frame for id=0x%08x",id);

   // Find Transaction
   if ( (tran = getTransaction(id)) == NULL ) {
     log_->debug("Invalid ID frame for id=0x%08x",id);
     return; // Bad id or post, drop frame
   }

   // Read tail error value, complete if error is set
   it = frame->endPayload()-sizeof(tail);
   std::copy(it,it + sizeof(tail), tail);
   if ( tail[0] != 0 ) {
      delMaster(id);

      if ( temp & 0x20000 ) tran->done(rim::AxiTimeout);
      else if ( temp & 0x10000 ) tran->done(rim::AxiFail);
      else tran->done(temp);
      log_->debug("Error detected for ID id=0x%08x",id);
      return;
   }

   // Copy data if read
   it = frame->begin() + sizeof(header);
   std::copy(it,it+(size()-(sizeof(header) + sizeof(tail))))

   frame->read(&temp,4,4);
   if ( (temp & 0xC0000000) == 0 ) {
      size = frame->getPayload() - 12;
      cnt  = 8;

      iter = frame->startRead(cnt,size);

      do {
         m->setTransactionData(id,iter->data(),iter->total(),iter->size());
      } while (frame->nextRead(iter));
      cnt += size;
   }

   delMaster(id);
   m->doneTransaction(id,0);
}

