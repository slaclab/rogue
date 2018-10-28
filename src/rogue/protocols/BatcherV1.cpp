/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Batcher Version 1
 * ----------------------------------------------------------------------------
 * File          : BatcherV1.h
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 10/26/2018
 *-----------------------------------------------------------------------------
 * Description :
 *    AXI Batcher V1
 *
 * The batcher protocol starts with a super header followed by a number of
 * frames each with a tail to define the boundaries of each frame.
 *
 * Super Header:
 *
 *    Byte 0:
 *       Bits 3:0 = Version = 1
 *       Bits 7:4 = Width = 2 * 2 ^ val Bytes
 *    Byte 1:
 *       Bits 15:8 = Sequence # for debug
 *    The reset of the width is padded with zeros
 *
 * Frame Tail: Tail size is always equal to the interfae width or 64-bis
 *             whichever is larger. Padded values are 0 (higher bytes).
 *
 *    Word 0:
 *       bits 31:0 = size
 *    Word 1:
 *       bits  7:0  = Destination
 *       bits 15:8  = First user
 *       bits 23:16 = Last user
 *       bits 31:24 = Valid bytes in last field
 *
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
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/protocols/BatcherV1.h>
#include <rogue/Logging.h>
#include <rogue/GilRelease.h>
#include <math.h>

namespace rp  = rogue::protocols;
namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Class creation
rp::BatcherV1Ptr rp::BatcherV1::create() {
   rp::BatcherV1Ptr p = boost::make_shared<rp::BatcherV1>();
   return(p);
}

//! Setup class in python
void rp::BatcherV1::setup_python() {
#ifndef NO_PYTHON
   bp::class_<rp::BatcherV1, rp::BatcherV1Ptr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("BatcherV1",bp::init<>());
#endif
}

//! Creator with version constant
rp::BatcherV1::BatcherV1() : ris::Master(), ris::Slave() { 
   log_ = rogue::Logging::create("BatcherV1");
}

//! Deconstructor
rp::BatcherV1::~BatcherV1() {}

//! Accept a frame from master
void rp::BatcherV1::acceptFrame ( ris::FramePtr frame ) {
   uint8_t  temp;
   uint8_t  width;
   uint8_t  tSize;
   uint8_t  sequence;
   uint32_t fSize;
   uint32_t fJump;
   uint32_t flags;
   uint8_t  dest;
   uint8_t  fUser;
   uint8_t  lUser;
   uint8_t  lSize;
   uint32_t rem;

   ris::FramePtr  nFrame;

   std::vector<ris::FramePtr> list;
   std::vector<ris::FramePtr>::iterator lIter;

   ris::FrameIterator beg;
   ris::FrameIterator mark;
   ris::FrameIterator tail;

   // Lock frame
   rogue::GilRelease noGil;
   ris::FrameLockPtr lock = frame->lock();
 
   // Drop errored frames
   if ( (frame->getError()) ) {
      log_->warning("Dropping frame due to error: 0x%x",frame->getError());
      return;
   }

   // Drop small frames
   if ( (rem = frame->getPayload()) < 16)  {
      log_->warning("Dropping small frame size = %i",frame->getPayload());
      return;
   }

   // Get version & size
   beg = frame->beginRead();
   ris::fromFrame(beg, 1, &temp);

   // Check version, convert width
   if ( (temp & 0x4) != 1 ) {
      log_->warning("Version mismatch. Got %i",(temp&0x4));
      return;
   }
   width = (uint32_t)pow(float((temp >> 4) & 0xF),2.0) * 2;

   // Set tail size, min 64-bits
   tSize = (width < 8)?8:width;

   // Get sequence #
   ris::fromFrame(beg, 1, &sequence);

   // Frame needs to large enough for header + 1 tail
   if ( rem < (width + tSize)) {
      log_->warning("Not enough space (%i) for tail (%i) + header (%i)",rem,width,tSize);
      return;
   }

   // Skip the rest of the header, compute remaining frame size
   beg += (width-2);
   rem -= width;

   // Set marker to end of frame
   mark = frame->endRead();

   // Process each frame, stop when we have reached just after the header
   while (mark != beg) {

      // sanity check
      if ( rem < tSize ) {
         log_->warning("Not enough space (%i) for tail (%i)",rem,tSize);
         return;
      }

      // Jump to start of the tail
      mark -= tSize;
      rem  -= tSize;
      
      // Get tail data, use a new iterator
      tail = mark;
      ris::fromFrame(tail, 4, &fSize);
      ris::fromFrame(tail, 1, &dest);
      ris::fromFrame(tail, 1, &fUser);
      ris::fromFrame(tail, 1, &lUser);
      ris::fromFrame(tail, 1, &lSize);

      // Round up rewind amount to width
      if ( (fSize % width) == 0) fJump = fSize;
      else fJump = ((fSize / width) + 1) * width;

      // Not enough data for rewind value
      if ( fJump > rem ) {
         log_->warning("Not enough space (%i) for frame (%i)",rem,fJump);
         return;
      }

      // Set marker to start of data 
      mark -= fJump;
      rem  -= fJump;

      // Create a new frame
      nFrame = reqFrame(fSize,true);
      std::copy(mark,(mark+fSize),nFrame->beginWrite());
      nFrame->setPayload(fSize);

      // Set flags
      nFrame->setFirstUser(fUser);
      nFrame->setLastUser(lUser);
      nFrame->setChannel(dest);
      
      // Add to vector
      list.push_back(nFrame);
   }

   // Walk through vector backwards and send frames
   if ( list.size() > 0 ) {
      lIter = list.end();
      do {
         lIter--;
         sendFrame(*lIter);
      } while(lIter != list.begin());
   }
}

