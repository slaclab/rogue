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
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <rogue/common.h>
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
   debug_ = 0;
}

//! Destructor
ris::Slave::~Slave() { }

//! Set debug message size
void ris::Slave::setDebug(uint32_t debug, std::string name) {
   name_  = name;
   debug_ = debug;
}

//! Accept a frame from master
void ris::Slave::acceptFrame ( ris::FramePtr frame ) {
   uint32_t x;
   uint8_t  val;

   if ( debug_ > 0 ) {
      Logging log(name_.c_str());
      char buffer[1000];

      log.log("info","Got Size=%i, Data:",name_.c_str(),frame->getPayload());
      sprintf(buffer,"     ");

      for (x=0; (x < debug_ && x < frame->getPayload()); x++) {
         frame->read(&val,x,1);

         sprintf(buffer + strlen(buffer)," 0x%.2x",val);
         if (( (x+1) % 10 ) == 0) 
            log.log("info",buffer);
            sprintf(buffer,"     ");
      }

      if ( strlen(buffer) > 5 ) log.log("info",buffer);
   }
}

//! Accept frame
void ris::SlaveWrap::acceptFrame ( ris::FramePtr frame ) {
   bool found;

   found = false;

   // Not sure if this is (and release) are ok if calling from python to python
   // It appears we need to lock before calling get_override
   PyGILState_STATE pyState = PyGILState_Ensure();

   if (boost::python::override pb = this->get_override("_acceptFrame")) {
      found = true;
      try {
         pb(frame);
      } catch (...) {
         PyErr_Print();
      }
   }
   PyGILState_Release(pyState);

   if ( ! found ) ris::Slave::acceptFrame(frame);
}

//! Default accept frame call
void ris::SlaveWrap::defAcceptFrame ( ris::FramePtr frame ) {
   ris::Slave::acceptFrame(frame);
}

void ris::Slave::setup_python() {

   bp::class_<ris::SlaveWrap, ris::SlaveWrapPtr, boost::noncopyable>("Slave",bp::init<>())
      .def("create",         &ris::Slave::create)
      .staticmethod("create")
      .def("setDebug",       &ris::Slave::setDebug)
      .def("_acceptFrame",   &ris::Slave::acceptFrame, &ris::SlaveWrap::defAcceptFrame)
   ;

   bp::implicitly_convertible<ris::SlavePtr, ris::PoolPtr>();

}

