/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Register Protocol (SRP) SrpV3
 * ----------------------------------------------------------------------------
 * File          : SrpV3.cpp
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 09/17/2016
 * Last update   : 09/17/2016
 *-----------------------------------------------------------------------------
 * Description :
 *    SRP protocol bridge, Version 3
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
#include <rogue/protocols/srp/SrpV3.h>
#include <rogue/Logging.h>
#include <rogue/GilRelease.h>

namespace bp = boost::python;
namespace rps = rogue::protocols::srp;
namespace rim = rogue::interfaces::memory;
namespace ris = rogue::interfaces::stream;

//! Class creation
rps::SrpV3Ptr rps::SrpV3::create () {
   rps::SrpV3Ptr p = boost::make_shared<rps::SrpV3>();
   return(p);
}

//! Setup class in python
void rps::SrpV3::setup_python() {

   bp::class_<rps::SrpV3, rps::SrpV3Ptr, bp::bases<ris::Master,ris::Slave,rim::Slave>,boost::noncopyable >("SrpV3",bp::init<>());

   bp::implicitly_convertible<rps::SrpV3Ptr, ris::MasterPtr>();
   bp::implicitly_convertible<rps::SrpV3Ptr, ris::SlavePtr>();
   bp::implicitly_convertible<rps::SrpV3Ptr, rim::SlavePtr>();

}

//! Creator with version constant
rps::SrpV3::SrpV3() : ris::Master(), ris::Slave(), rim::Slave(4,4096) { 
   log_ = rogue::Logging::create("SrpV3");
}

//! Deconstructor
rps::SrpV3::~SrpV3() {}

//! Setup header, return frame size
bool rps::SrpV3::setupHeader(rim::TransactionPtr tran, uint32_t *header, uint32_t &frameLen, bool tx) {
   bool doWrite = true;

   // Bits 7:0 of first 32-bit word are version
   header[0] = 0x03;

   // Bits 9:8: 0x0 = read, 0x1 = write, 0x2 = posted write
   switch ( tran->type() ) {
      case rim::Write : header[0] |= 0x100; break;
      case rim::Post  : header[0] |= 0x200; break;
      default: doWrite = false; break; // Read or verify
   }
   
   // Bits 13:10 not used in gen frame
   // Bit 14 = ignore mem resp
   // Bit 23:15 = Unused
   // Bit 31:24 = timeout count
   header[0] |= 0x0A000000;

   // Header word 1, transaction ID
   header[1] = tran->id();

   // Header word 2, lower address
   header[2] = tran->address() & 0xFFFFFFFF;

   // Header word 3, upper address
   header[3] = (tran->address() >> 32) & 0xFFFFFFFF;

   // Header word 4, request size
   header[4] = tran->size()-1;

   // Determine frame length
   frameLen = HeadLen;

   // Transmit with write data
   if ( tx && doWrite ) frameLen += tran->size();

   // Receive frames
   else if ( ! tx ) frameLen += tran->size() + TailLen;

   return doWrite;
}

//! Post a transaction
void rps::SrpV3::doTransaction(rim::TransactionPtr tran) {
   ris::Frame::iterator fIter;
   rim::Transaction::iterator tIter;
   ris::FramePtr  frame;
   uint32_t frameSize;
   uint32_t header[HeadLen/4];
   bool doWrite;

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

   // Compute header and frame size
   doWrite = setupHeader(tran,header,frameSize,true);

   // Request frame
   frame = reqFrame(frameSize,true);
   frame->setPayload(frameSize);

   // Setup iterators
   rogue::GilRelease noGil;
   boost::unique_lock<boost::mutex> lock(tran->lock);
   fIter = frame->beginWrite();
   tIter = tran->begin();

   // Write header
   ris::toFrame(fIter,HeadLen,header);

   // Write data
   if ( doWrite ) std::copy(tIter,tIter+tran->size(),fIter);

   lock.unlock(); // Done with iterator

   if ( tran->type() == rim::Post ) tran->done(0);
   else addTransaction(tran);

   log_->debug("Send frame for id=0x%08x, addr 0x%08x. Size=%i, type=%i",tran->id(),tran->address(),tran->size(),tran->type());
   log_->debug("Send frame header: 0x%0.8x 0x%0.8x 0x%0.8x 0x%0.8x 0x%0.8x",
         header[0],header[1],header[2],header[3],header[4]);
   sendFrame(frame);
}

//! Accept a frame from master
void rps::SrpV3::acceptFrame ( ris::FramePtr frame ) {
   ris::Frame::iterator fIter;
   rim::Transaction::iterator tIter;
   rim::TransactionPtr tran;
   uint32_t header[HeadLen/4];
   uint32_t expHeader[HeadLen/4];
   uint32_t expFrameLen;
   uint32_t tail[TailLen/4];
   uint32_t id;
   bool     doWrite;
   uint32_t fSize;

   // Check frame size
   if ( (fSize = frame->getPayload()) < HeadLen ) {
      log_->info("Got undersize frame size = %i",fSize);
      return; // Invalid frame, drop it
   }

   // Setup Frame iterator
   fIter = frame->beginRead();

   // Get the header
   ris::fromFrame(fIter,HeadLen,header);

   // Extract the id
   id = header[1];
   log_->debug("Got frame id=%i, header: 0x%0.8x 0x%0.8x 0x%0.8x 0x%0.8x 0x%0.8x",
         id, header[0],header[1],header[2],header[3],header[4]);

   // Find Transaction
   if ( (tran = getTransaction(id)) == NULL ) {
     log_->debug("Invalid ID frame for id=0x%08x",id);
     return; // Bad id or post, drop frame
   }

   // Setup transaction iterator
   rogue::GilRelease noGil;
   boost::unique_lock<boost::mutex> lock(tran->lock);

   // Transaction expired
   if ( tran->expired() ) {
      log_->debug("Transaction expired. Id=%i",id);
      delTransaction(tran->id());
      return;
   }
   tIter = tran->begin();

   // Setup expect header and length
   doWrite = setupHeader(tran,expHeader,expFrameLen,false);

   // Verify frame size, drop frame
   if ( (fSize != expFrameLen) ||
        (header[4]+1) != tran->size() ) {
      delTransaction(id);
      log_->debug("Size mismatch id=0x%08x",id);
      return;
   }

   // Check header
   if ( ((header[0] & 0xFFFFC3FF) != expHeader[0]) ||
         (header[1] != expHeader[1]) || (header[2] != expHeader[2]) ||
         (header[3] != expHeader[3]) || (header[4] != expHeader[4]) ) {
     log_->debug("Bad header for %i",id);
     return;
   }

   // Read tail error value, complete if error is set
   fIter = frame->endRead()-TailLen;
   ris::fromFrame(fIter,TailLen,tail);
   if ( tail[0] != 0 ) {
      delTransaction(tran->id());

      if ( tail[0] & 0xFF) tran->done(rim::AxiFail | (tail[0] & 0xFF));
      else if ( tail[0] & 0x100 ) tran->done(rim::AxiTimeout);
      else tran->done(tail[0]);
      log_->debug("Error detect id=0x%08x",id);
      return;
   }

   // Copy data if read
   if ( ! doWrite ) {
      fIter = frame->beginRead() + HeadLen;
      std::copy(fIter,fIter+tran->size(),tIter);
   }
   lock.unlock(); // Done with iterator

   delTransaction(tran->id());
   tran->done(0);
}

