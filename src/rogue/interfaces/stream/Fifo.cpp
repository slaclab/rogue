/**
 *-----------------------------------------------------------------------------
 * Title         : AXI Stream FIFO
 * ----------------------------------------------------------------------------
 * File          : Fifo.cpp
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 02/02/2018
 *-----------------------------------------------------------------------------
 * Description :
 *    AXI Stream FIFO
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
#include <thread>
#include <memory>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/FrameLock.h>
#include <rogue/interfaces/stream/FrameIterator.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/interfaces/stream/Fifo.h>
#include <rogue/Logging.h>
#include <rogue/GilRelease.h>

namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Class creation
ris::FifoPtr ris::Fifo::create(uint32_t maxDepth, uint32_t trimSize, bool noCopy) {
   ris::FifoPtr p = std::make_shared<ris::Fifo>(maxDepth,trimSize,noCopy);
   return(p);
}

//! Setup class in python
void ris::Fifo::setup_python() {
#ifndef NO_PYTHON
   bp::class_<ris::Fifo, ris::FifoPtr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("Fifo",bp::init<uint32_t,uint32_t,bool>());
#endif
}

//! Creator with version constant
ris::Fifo::Fifo(uint32_t maxDepth, uint32_t trimSize, bool noCopy ) : ris::Master(), ris::Slave() { 
   maxDepth_ = maxDepth;
   trimSize_ = trimSize;
   noCopy_   = noCopy;

   queue_.setThold(maxDepth);

   log_ = rogue::Logging::create("stream.Fifo");

   // Start read thread
   threadEn_ = true;
   thread_ = new std::thread(&ris::Fifo::runThread, this);
}

//! Deconstructor
ris::Fifo::~Fifo() {
   //queue_.stop();
   threadEn_ = false;
   thread_->join();
}

//! Accept a frame from master
void ris::Fifo::acceptFrame ( ris::FramePtr frame ) {
   uint32_t       size;
   ris::BufferPtr buff;
   ris::FramePtr  nFrame;
   ris::Frame::BufferIterator src;
   ris::Frame::iterator dst;

   // FIFO is full, drop frame
   if ( queue_.busy()  ) return;

   rogue::GilRelease noGil;
   ris::FrameLockPtr lock = frame->lock();

   // Do we copy the frame?
   if ( noCopy_ ) nFrame = frame;
   else{

      // Get size, adjust if trim is enabled
      size = frame->getPayload();
      if ( trimSize_ != 0 && trimSize_ < size ) size = trimSize_;

      // Request a new frame to hold the data
      nFrame = reqFrame(size,true);

      // Get destination pointer
      dst = nFrame->beginWrite();

      // Copy the frame, attempt to be effecient by iterating through source buffers
      for (src=frame->beginBuffer(); src != frame->endBuffer(); ++src) 
         dst = std::copy((*src)->begin(), (*src)->endPayload(), dst);

      nFrame->setPayload(size);
   }

   // Append to buffer
   queue_.push(nFrame);
}

//! Thread background
void ris::Fifo::runThread() {
   ris::FramePtr frame;
   log_->logThreadId();

   while(threadEn_) {
      if ( (frame = queue_.pop()) != NULL ) sendFrame(queue_.pop());
   }
}

