/**
 *-----------------------------------------------------------------------------
 * Title      : RSSI Core Class
 * ----------------------------------------------------------------------------
 * File       : Core.h
 * Created    : 2017-01-07
 * Last update: 2017-01-07
 * ----------------------------------------------------------------------------
 * Description:
 * UDP Core
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
#include <rogue/protocols/rssi/Core.h>
#include <rogue/protocols/rssi/Transport.h>
#include <rogue/protocols/rssi/Application.h>
#include <rogue/protocols/rssi/Controller.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <rogue/common.h>

namespace rpr = rogue::protocols::rssi;
namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Class creation
rpr::CorePtr rpr::Core::create (uint32_t segSize) {
   rpr::CorePtr r = boost::make_shared<rpr::Core>(segSize);
   return(r);
}

void rpr::Core::setup_python() {

   bp::class_<rpr::Core, rpr::CorePtr, boost::noncopyable >("Core",bp::init<uint32_t>())
      .def("create",         &rpr::Core::create)
      .staticmethod("create")
      .def("transport",      &rpr::Core::transport)
      .def("application",    &rpr::Core::application)
   ;

}

//! Creator
rpr::Core::Core (uint32_t segSize) {
   app_   = rpr::Application::create();
   tran_  = rpr::Transport::create();
   cntl_  = rpr::Controller::create(segSize,tran_,app_);

   app_->setController(cntl_);
   tran_->setController(cntl_);
}

//! Destructor
rpr::Core::~Core() { }


//! Get transport interface
rpr::TransportPtr rpr::Core::transport() {
   return(tran_);
}

//! Application module
rpr::ApplicationPtr rpr::Core::application() {
   return(app_);
}

//! Get state
bool rpr::Core::getOpen() {
   return(cntl_->getOpen());
}

//! Get Down Count
uint32_t rpr::Core::getDownCount() {
   return(cntl_->getDownCount());
}

//! Get Drop Count
uint32_t rpr::Core::getDropCount() {
   return(cntl_->getDropCount());
}

//! Get Retran Count
uint32_t rpr::Core::getRetranCount() {
   return(cntl_->getRetranCount());
}

