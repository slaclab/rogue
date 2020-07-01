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
#include <memory>
#include <rogue/GilRelease.h>
#include <rogue/ScopedGil.h>
#include <rogue/Logging.h>
#include <string.h>

namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Class creation
ris::SlavePtr ris::Slave::create () {
   ris::SlavePtr slv = std::make_shared<ris::Slave>();
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

void ris::Slave::stop () {
}

//! Set debug message size
void ris::Slave::setDebug(uint32_t debug, std::string name) {
   debug_ = debug;
   log_   = rogue::Logging::create(name.c_str());
}

//! Accept a frame from master
void ris::Slave::acceptFrame ( ris::FramePtr frame ) {
   ris::FrameIterator it;

   uint32_t count;
   uint8_t  val;

   rogue::GilRelease noGil;
   ris::FrameLockPtr lock = frame->lock();

   frameCount_++;
   frameBytes_ += frame->getPayload();

   if ( debug_ > 0 ) {
      char buffer[1000];

      log_->critical("Got Size=%i, Error=%i, Data:",frame->getPayload(),frame->getError());
      sprintf(buffer,"     ");

      count = 0;
      for (it = frame->begin(); (count < debug_) && (it != frame->end()); ++it) {
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

#ifndef NO_PYTHON

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

#endif

//! Get frame counter
uint64_t ris::Slave::getFrameCount() {
   return(frameCount_);
}

//! Get byte counter
uint64_t ris::Slave::getByteCount() {
   return(frameBytes_);
}

void ris::Slave::setup_python() {
#ifndef NO_PYTHON

   bp::class_<ris::SlaveWrap, ris::SlaveWrapPtr, boost::noncopyable>("Slave",bp::init<>())
      .def("setDebug",       &ris::Slave::setDebug)
      .def("_acceptFrame",   &ris::Slave::acceptFrame, &ris::SlaveWrap::defAcceptFrame)
      .def("getFrameCount",  &ris::Slave::getFrameCount)
      .def("getByteCount",   &ris::Slave::getByteCount)
      .def("_stop",          &ris::Slave::stop)
      .def("getAllocCount",  &ris::Pool::getAllocCount)
      .def("getAllocBytes",  &ris::Pool::getAllocBytes)
      .def("setFixedSize",   &ris::Pool::setFixedSize)
      .def("getFixedSize",   &ris::Pool::getFixedSize)
      .def("setPoolSize",    &ris::Pool::setPoolSize)
      .def("getPoolSize",    &ris::Pool::getPoolSize)
      .def("__lshift__",     &ris::Slave::lshiftPy)
   ;

   bp::implicitly_convertible<ris::SlavePtr, ris::PoolPtr>();
#endif
}


#ifndef NO_PYTHON

// Support << operator in python
bp::object ris::Slave::lshiftPy ( bp::object p ) {
   ris::MasterPtr mst;

   // First Attempt to access object as a stream master
   boost::python::extract<ris::MasterPtr> get_master(p);

   // Test extraction
   if ( get_master.check() ) mst = get_master();

   // Otherwise look for indirect call
   else if ( PyObject_HasAttrString(p.ptr(), "_getStreamMaster" ) ) {

      // Attempt to convert returned object to master pointer
      boost::python::extract<ris::MasterPtr> get_master(p.attr("_getStreamMaster")());

      // Test extraction
      if ( get_master.check() ) mst = get_master();
   }

   if ( mst != NULL ) mst->addSlave(rogue::EnableSharedFromThis<ris::Slave>::shared_from_this());
   else throw(rogue::GeneralError::create("stream::Slave::lshiftPy","Attempt to use << with incompatable stream master"));

   return p;
}

#endif

//! Support << operator in C++
ris::MasterPtr & ris::Slave::operator <<(ris::MasterPtr & other) {
   other->addSlave(rogue::EnableSharedFromThis<ris::Slave>::shared_from_this());
   return other;
}

