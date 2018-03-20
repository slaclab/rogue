/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Register Protocol (SRP) Fifo
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
#include <boost/thread.hpp>
#include <boost/make_shared.hpp>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/FrameIterator.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/interfaces/stream/Fifo.h>
#include <rogue/Logging.h>
#include <sys/syscall.h>

namespace bp = boost::python;
namespace ris = rogue::interfaces::stream;

//! Class creation
ris::FifoPtr ris::Fifo::create(uint32_t maxDepth, uint32_t trimSize) {
   ris::FifoPtr p = boost::make_shared<ris::Fifo>(maxDepth,trimSize);
   return(p);
}

//! Setup class in python
void ris::Fifo::setup_python() {
   bp::class_<ris::Fifo, ris::FifoPtr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("Fifo",bp::init<uint32_t,uint32_t>());
}

//! Creator with version constant
ris::Fifo::Fifo(uint32_t maxDepth, uint32_t trimSize ) : ris::Master(), ris::Slave() { 
   maxDepth_ = maxDepth;
   trimSize_ = trimSize;

   queue_.setThold(maxDepth);

   log_ = rogue::Logging::create("Fifo");

   // Start read thread
   thread_ = new boost::thread(boost::bind(&ris::Fifo::runThread, this));
}

//! Deconstructor
ris::Fifo::~Fifo() {}

//! Accept a frame from master
void ris::Fifo::acceptFrame ( ris::FramePtr frame ) {
   uint32_t       size;
   ris::BufferPtr buff;
   ris::FramePtr  nFrame;

   // FIFO is full, drop frame
   if ( queue_.busy()  ) return;

   // Get size, adjust if trim is enabled
   size = frame->getPayload();
   if ( trimSize_ != 0 && trimSize_ < size ) size = trimSize_;

   // Request a new frame to hold the data
   nFrame = reqFrame(size,true);

   // Copy the frame
   std::copy(frame->beginRead(), frame->beginRead()+size, nFrame->beginWrite());
   nFrame->setPayload(size);

   // Append to buffer
   queue_.push(nFrame);
}

//! Thread background
void ris::Fifo::runThread() {
   log_->info("PID=%i, TID=%li",getpid(),syscall(SYS_gettid));

   try {
      while(1) {
         sendFrame(queue_.pop());
      }
   } catch (boost::thread_interrupted&) { }
}

