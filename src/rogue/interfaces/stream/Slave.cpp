/**
 *-----------------------------------------------------------------------------
 * Title      : Stream interface slave
 * ----------------------------------------------------------------------------
 * File       : Slave.cpp
 * Created    : 2016-09-16
 * ----------------------------------------------------------------------------
 * Description:
 * Stream interface slave
 *    The function calls in this are a mess! create buffer, allocate buffer, etc
 *    need to be reworked.
 * ----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to 
 * the license terms in the LICENSE.txt file found in the top-level directory 
 * of this distribution and at: 
 *    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
 * No part of the rogue software platform, including this file, may be 
 * copied, modified, propagated, or distributed except according to the terms 
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
**/
#include <unistd.h>
#include <string>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/FrameLock.h>
#include <rogue/interfaces/stream/FrameIterator.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <rogue/GilRelease.h>
#include <rogue/ScopedGil.h>
#include <rogue/Logging.h>

namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Class creation
ris::SlavePtr ris::Slave::create () {
   ris::SlavePtr slv = boost::make_shared<ris::Slave>();
   return(slv);
}

//! Creator
ris::Slave::Slave() {
   debug_      = 0;
   frameCount_ = 0;
   frameBytes_ = 0;
}

//! Destructor
ris::Slave::~Slave() { }

//! Set debug message size
void ris::Slave::setDebug(uint32_t debug, std::string name) {
   debug_ = debug;
   log_   = rogue::Logging::create(name.c_str());
}

//! Accept a frame from master
void ris::Slave::acceptFrame ( ris::FramePtr frame ) {
   ris::Frame::iterator it;

   uint32_t count;
   uint8_t  val;

   rogue::GilRelease noGil;
   ris::FrameLockPtr lock = frame->lock();

   frameCount_++;
   frameBytes_ += frame->getPayload();

   if ( debug_ > 0 ) {
      char buffer[1000];

      log_->critical("Got Size=%i, Data:",frame->getPayload());
      sprintf(buffer,"     ");

      count = 0;
      for (it = frame->beginRead(); (count < debug_) && (it != frame->endRead()); ++it) {
         count++;
         val = *it;

         snprintf(buffer + strlen(buffer),1000-strlen(buffer)," 0x%.2x",val);
         if (( (count+1) % 8 ) == 0) {
            log_->critical(buffer);
            sprintf(buffer,"     ");
         }
      }

      if ( strlen(buffer) > 5 ) log_->log(100,buffer);
   }
}

//! Accept frame
void ris::SlaveWrap::acceptFrame ( ris::FramePtr frame ) {
   {
      rogue::ScopedGil gil;

      if (boost::python::override pb = this->get_override("_acceptFrame")) {
         try {
            pb(frame);
            return;
         } catch (...) {
            PyErr_Print();
         }
      }
   }
   ris::Slave::acceptFrame(frame);
}

//! Default accept frame call
void ris::SlaveWrap::defAcceptFrame ( ris::FramePtr frame ) {
   ris::Slave::acceptFrame(frame);
}


//! Get frame counter
uint64_t ris::Slave::getFrameCount() {
   return(frameCount_);
}

//! Get byte counter
uint64_t ris::Slave::getByteCount() {
   return(frameBytes_);
}

void ris::Slave::setup_python() {

   bp::class_<ris::SlaveWrap, ris::SlaveWrapPtr, boost::noncopyable>("Slave",bp::init<>())
      .def("setDebug",       &ris::Slave::setDebug)
      .def("_acceptFrame",   &ris::Slave::acceptFrame, &ris::SlaveWrap::defAcceptFrame)
      .def("getFrameCount",  &ris::Slave::getFrameCount)
      .def("getByteCount",   &ris::Slave::getByteCount)
   ;

   bp::implicitly_convertible<ris::SlavePtr, ris::PoolPtr>();

}

