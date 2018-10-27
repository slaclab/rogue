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
#include <rogue/interfaces/stream/BatcherV2.h>
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
rp::BatcherV2Ptr rp::BatcherV2::create() {
   rp::BatcherV2Ptr p = boost::make_shared<rp::BatcherV2>();
   return(p);
}

//! Setup class in python
void rp::BatcherV2::setup_python() {
#ifndef NO_PYTHON
   bp::class_<rp::BatcherV2, rp::BatcherV2Ptr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("BatcherV1",bp::init<>());
#endif
}

//! Creator with version constant
rp::BatcherV2::BatcherV2() : ris::Master(), ris::Slave() { 
   log_ = rogue::Logging::create("BatcherV2");
}

//! Deconstructor
rp::BatcherV2::~BatcherV2() {}

//! Accept a frame from master
void rp::BatcherV2::acceptFrame ( ris::FramePtr frame ) {
   uint8_t  temp;
   uint8_t  width;
   uint8_t  tSize;
   uint8_t  sequence;
   uint32_t fSize;
   uint8_t  dest;
   uint8_t  fUser;
   uint8_t  lUser;
   uint8_t  lSize;
   uint32_t rem;

   ris::FramePtr  nFrame;

   std::vector<ris::FramePtr> list;
   std::vector<ris::FramePtr>::iterator lIter;

   rip::FrameIterator beg;
   rip::FrameIterator mark;
   rip::FrameIterator tail;

   // Lock frame
   rogue::GilRelease noGil;
   ris::FrameLockPtr lock = frame->lock();
  
   // Drop errored frames or small frames, assign remaining size
   if ( (frame->getError()) || ((rem = frame->getPayload()) < 16) ) return;

   // Get version & size
   beg = frame->beginRead();
   ris::fromFrame(beg, 1, &temp);

   // Check version, convert width
   if ( (temp & 0x4) != 1 ) return;
   width = (uint32_t)pow(float((temp >> 4) & 0xF),2.0) * 2;

   // Set tail size, min 64-bits
   tSize = (width < 8)?8:width;

   // Get sequence #
   ris::fromFrame(beg, 1, &sequence);

   // Frame needs to large enough for header + 1 tail
   if ( rem < (width + tSize)) return;

   // Skip the rest of the header, compute remaining frame size
   beg += (width-16);
   rem -= width;

   // Set marker to end of frame
   mark = end;

   // Process each frame, stop when we have reached just after the header
   while (mark != beg) {

      // sanity check
      if ( rem < tSize ) return;

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
      tail = mark;

      // Not enough data for passed length
      if ( fSize > rem ) return;

      // Set marker to start of data
      // need to adjust this
      mark -= fSize;
      rem  -= fSize;

      // Create a new frame, add to vector
      newFrame = requestFrame(fSize,true);
      std::copy(mark,tail,newFrame->begWrite());
      newFrame->setPayload(fSize);
      list.append(newFrame);
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

