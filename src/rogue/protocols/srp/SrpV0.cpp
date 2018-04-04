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
#include <rogue/interfaces/stream/FrameLock.h>
#include <rogue/interfaces/stream/FrameIterator.h>
#include <rogue/interfaces/memory/Slave.h>
#include <rogue/interfaces/memory/Constants.h>
#include <rogue/interfaces/memory/Transaction.h>
#include <rogue/interfaces/memory/TransactionLock.h>
#include <rogue/protocols/srp/SrpV0.h>
#include <rogue/Logging.h>
#include <rogue/GilRelease.h>

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

//! Setup header, return frame size
bool rps::SrpV0::setupHeader(rim::TransactionPtr tran, uint32_t *header, uint32_t &headerLen, uint32_t &frameLen, bool tx) {
   bool doWrite = false;

   header[0] = tran->id();
   header[1] = (tran->address() >> 2) & 0x3FFFFFFF;
   header[2] = (tran->size()/4)-1; // reads

   // Build header for write
   if (tran->type() == rim::Write || tran->type() == rim::Post) {
      header[1] |= 0x40000000;
      frameLen  = (tran->size() + WrHeadLen + TailLen);
      headerLen = WrHeadLen;
      doWrite = true;
   }
   else if ( tx ) {
      frameLen  = RdHeadLen + TailLen;
      headerLen = RdHeadLen;
   }
   else {
      frameLen = (tran->size() + RxHeadLen + TailLen);
      headerLen = RxHeadLen;
   }

   return doWrite;
}

//! Post a transaction
void rps::SrpV0::doTransaction(rim::TransactionPtr tran) {
   ris::Frame::iterator fIter;
   rim::Transaction::iterator tIter;
   ris::FramePtr  frame;
   uint32_t frameSize;
   uint32_t header[MaxHeadLen/4];
   uint32_t tail[TailLen/4];
   uint32_t headerLen;
   bool     doWrite;

   // Size error
   if ((tran->address() % min()) != 0 ) {
      tran->done(rim::AddressError);
      return;
   }

   // Size error
   if ((tran->size() % min()) != 0 || tran->size() < min() || tran->size() > max()) {
      tran->done(rim::SizeError);
      return;
   }

   // Setup header and frame size
   doWrite = setupHeader(tran,header,headerLen,frameSize,true);

   // Request frame
   frame = reqFrame(frameSize,true);
   frame->setPayload(frameSize);

   // Setup iterators
   rogue::GilRelease noGil;
   rim::TransactionLockPtr lock = tran->lock();
   fIter = frame->beginWrite();
   tIter = tran->begin();

   // Write header
   ris::toFrame(fIter,headerLen,header); 

   // Write data
   if ( doWrite ) {
      std::copy(tIter,tIter+tran->size(),fIter);
      fIter += tran->size();
   }

   // Last field is zero
   tail[0] = 0;
   ris::toFrame(fIter,TailLen,tail); 

   if ( tran->type() == rim::Post ) tran->done(0);
   else addTransaction(tran);

   log_->debug("Send frame for id=%i, addr 0x%0.8x. Size=%i, type=%i, doWrite=%i",
               tran->id(),tran->address(),tran->size(),tran->type(),doWrite);
   log_->debug("Send frame for id=%i, header: 0x%0.8x 0x%0.8x 0x%0.8x",
               tran->id(),header[0],header[1],header[2]);

   sendFrame(frame);
}

//! Accept a frame from master
void rps::SrpV0::acceptFrame ( ris::FramePtr frame ) {
   ris::Frame::iterator fIter;
   rim::Transaction::iterator tIter;
   rim::TransactionPtr tran;
   uint32_t header[MaxHeadLen/4];
   uint32_t tail[TailLen/4];
   uint32_t id;
   uint32_t expHeader[MaxHeadLen/4];
   uint32_t expHeadLen;
   uint32_t expFrameLen;
   bool     doWrite;
   uint32_t fSize;

   rogue::GilRelease noGil();
   ris::FrameLockPtr fLock = frame->lock();

   // Check frame size
   if ( (fSize = frame->getPayload()) < 16 ) {
      log_->warning("Got undersize frame size = %i",fSize);
      return; // Invalid frame, drop it
   }

   // Setup frame iterator
   fIter = frame->beginRead();

   // Get the header
   ris::fromFrame(fIter,RxHeadLen,header);

   // Extract id from frame
   id = header[0];
   log_->debug("Got frame id=%i header: 0x%0.8x 0x%0.8x 0x%0.8x", 
               id, header[0],header[1],header[2]);

   // Find Transaction
   if ( (tran = getTransaction(id)) == NULL ) {
     log_->warning("Invalid ID frame for id=%i",id);
     return; // Bad id or post, drop frame
   }
   delTransaction(id);

   // Setup transaction iterator
   rim::TransactionLockPtr lock = tran->lock();

   // Transaction expired
   if ( tran->expired() ) {
      log_->warning("Transaction expired. Id=%i",id);
      return;
   }
   tIter = tran->begin();

   // Setup header and frame size
   doWrite = setupHeader(tran,expHeader,expHeadLen,expFrameLen,false);

   // Check frame size
   if ( fSize != expFrameLen ) {
      log_->warning("Bad receive length for %i exp=%i, got=%i",id,expFrameLen,fSize);
      return;
   }

   // Check header
   if ( memcmp(header,expHeader,RxHeadLen) != 0 ) {
     log_->warning("Bad header for %i",id);
     return;
   }

   // Read tail error value, complete if error is set
   fIter = frame->endRead()-TailLen;
   ris::fromFrame(fIter,TailLen,tail);
   if ( tail[0] != 0 ) {
      if ( tail[0] & 0x20000 ) tran->done(rim::AxiTimeout);
      else if ( tail[0] & 0x10000 ) tran->done(rim::AxiFail);
      else tran->done(tail[0]);
      log_->warning("Error detected for ID id=%i, tail=0x%0.8x",id,tail[0]);
      return;
   }

   // Copy data if read
   if ( ! doWrite ) {
      fIter = frame->beginRead() + RxHeadLen;
      std::copy(fIter,fIter+tran->size(),tIter);
   }

   // Done
   tran->done(0);
}

