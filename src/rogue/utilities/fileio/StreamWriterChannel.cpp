/**
 *-----------------------------------------------------------------------------
 * Title         : Data file writer utility. Channel interface.
 * ----------------------------------------------------------------------------
 * File          : StreamWriterChannel.cpp
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 09/28/2016
 * Last update   : 09/28/2016
 *-----------------------------------------------------------------------------
 * Description :
 *    Class to act as a slave interface to the StreamWriterChannel. Each
 *    slave is associated with a tag. The tag is included in the bank header
 *    of each write.
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
#include <rogue/utilities/fileio/StreamWriterChannel.h>
#include <rogue/utilities/fileio/StreamWriter.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/FrameLock.h>
#include <stdint.h>
#include <boost/thread.hpp>
#include <boost/make_shared.hpp>
#include <rogue/GilRelease.h>

namespace ris = rogue::interfaces::stream;
namespace ruf = rogue::utilities::fileio;

#ifndef NO_PYTHON
#include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Class creation
ruf::StreamWriterChannelPtr ruf::StreamWriterChannel::create (ruf::StreamWriterPtr writer, uint8_t channel) {
   ruf::StreamWriterChannelPtr s = boost::make_shared<ruf::StreamWriterChannel>(writer,channel);
   return(s);
}

//! Setup class in python
void ruf::StreamWriterChannel::setup_python() {
#ifndef NO_PYTHON
   bp::class_<ruf::StreamWriterChannel, ruf::StreamWriterChannelPtr, bp::bases<ris::Slave>, boost::noncopyable >("StreamWriterChannel",bp::no_init)
       .def("getFrameCount", &ruf::StreamWriterChannel::getFrameCount)
       .def("waitFrameCount", &ruf::StreamWriterChannel::waitFrameCount)
       ;
   bp::implicitly_convertible<ruf::StreamWriterChannelPtr, ris::SlavePtr>();
#endif
}

//! Creator
ruf::StreamWriterChannel::StreamWriterChannel(ruf::StreamWriterPtr writer, uint8_t channel) {
   writer_  = writer;
   channel_ = channel;
   frameCount_ = 0;
}

//! Deconstructor
ruf::StreamWriterChannel::~StreamWriterChannel() { }

//! Accept a frame from master
void ruf::StreamWriterChannel::acceptFrame ( ris::FramePtr frame ) {
   rogue::GilRelease noGil;
   ris::FrameLockPtr fLock = frame->lock();
   boost::unique_lock<boost::mutex> lock(mtx_);
   writer_->writeFile (channel_, frame);
   frameCount_++;
   lock.unlock();
   cond_.notify_all();
}

uint32_t ruf::StreamWriterChannel::getFrameCount() {
  return frameCount_;
}


void ruf::StreamWriterChannel::setFrameCount(uint32_t count) {
  rogue::GilRelease noGil;
  boost::unique_lock<boost::mutex> lock(mtx_);
  frameCount_ = count;
}

void ruf::StreamWriterChannel::waitFrameCount(uint32_t count) {
  rogue::GilRelease noGil;
  boost::unique_lock<boost::mutex> lock(mtx_);
  while (frameCount_ < count) {
    cond_.timed_wait(lock, boost::posix_time::microseconds(1000));
  }
}

