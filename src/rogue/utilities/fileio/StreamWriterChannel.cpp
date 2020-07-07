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
#include <thread>
#include <memory>
#include <rogue/GilRelease.h>
#include <sys/time.h>

namespace ris = rogue::interfaces::stream;
namespace ruf = rogue::utilities::fileio;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Class creation
ruf::StreamWriterChannelPtr ruf::StreamWriterChannel::create (ruf::StreamWriterPtr writer, uint8_t channel) {
   ruf::StreamWriterChannelPtr s = std::make_shared<ruf::StreamWriterChannel>(writer,channel);
   return(s);
}

//! Setup class in python
void ruf::StreamWriterChannel::setup_python() {
#ifndef NO_PYTHON
   bp::class_<ruf::StreamWriterChannel, ruf::StreamWriterChannelPtr, bp::bases<ris::Slave>, boost::noncopyable >("StreamWriterChannel",bp::no_init)
       .def("getFrameCount", &ruf::StreamWriterChannel::getFrameCount)
       .def("waitFrameCount", &ruf::StreamWriterChannel::waitFrameCount)
       .def("setFrameCount", &ruf::StreamWriterChannel::setFrameCount)
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
   uint8_t ichan;

   rogue::GilRelease noGil;
   ris::FrameLockPtr fLock = frame->lock();

   // Support for channelized traffic
   if ( channel_ == 0 ) ichan = frame->getChannel();
   else ichan = channel_;

   writer_->writeFile (ichan, frame);

   std::unique_lock<std::mutex> lock(mtx_);
   frameCount_++;
   cond_.notify_all();
}

uint32_t ruf::StreamWriterChannel::getFrameCount() {
  return frameCount_;
}


void ruf::StreamWriterChannel::setFrameCount(uint32_t count) {
  rogue::GilRelease noGil;
  std::unique_lock<std::mutex> lock(mtx_);
  frameCount_ = count;
}

bool ruf::StreamWriterChannel::waitFrameCount(uint32_t count, uint64_t timeout) {
   struct timeval endTime;
   struct timeval sumTime;
   struct timeval curTime;

   rogue::GilRelease noGil;
   std::unique_lock<std::mutex> lock(mtx_);

   if (timeout != 0 ) {
      gettimeofday(&curTime,NULL);

      div_t divResult = div(timeout,1000000);
      sumTime.tv_sec  = divResult.quot;
      sumTime.tv_usec = divResult.rem;

      timeradd(&curTime,&sumTime,&endTime);
   }

   while (frameCount_ < count) {
      cond_.wait_for(lock, std::chrono::microseconds(1000));

      if ( timeout != 0 ) {
         gettimeofday(&curTime,NULL);
         if ( timercmp(&curTime,&endTime,>) ) break;
      }
   }

   return (frameCount_ >= count);
}

