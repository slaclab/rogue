/**
 *-----------------------------------------------------------------------------
 * Title      : Packetizer Core Class
 * ----------------------------------------------------------------------------
 * File       : Core.h
 * Created    : 2017-01-07
 * Last update: 2017-01-07
 * ----------------------------------------------------------------------------
 * Description:
 * Packetizer Core
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
#include <rogue/protocols/packetizer/Core.h>
#include <rogue/protocols/packetizer/Transport.h>
#include <rogue/protocols/packetizer/Application.h>
#include <rogue/protocols/packetizer/Controller.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <rogue/common.h>

namespace rpp = rogue::protocols::packetizer;
namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Class creation
rpp::CorePtr rpp::Core::create (uint32_t segmentSize) {
   rpp::CorePtr r = boost::make_shared<rpp::Core>(segmentSize);
   return(r);
}

void rpp::Core::setup_python() {

   bp::class_<rpp::Core, rpp::CorePtr, boost::noncopyable >("Core",bp::init<uint32_t>())
      .def("create",         &rpp::Core::create)
      .staticmethod("create")
      .def("transport",      &rpp::Core::transport)
      .def("application",    &rpp::Core::application)
   ;

}

//! Creator
rpp::Core::Core (uint32_t segmentSize) {
   tran_  = rpp::Transport::create();
   cntl_  = rpp::Controller::create(segmentSize,tran_,app_);

   tran_->setController(cntl_);
}

//! Destructor
rpp::Core::~Core() { }


//! Get transport interface
rpp::TransportPtr rpp::Core::transport() {
   return(tran_);
}

//! Application module
rpp::ApplicationPtr rpp::Core::application(uint8_t dest) {
   if ( ! app_[dest] ) {
      app_[dest] = rpp::Application::create(dest);
      app_[dest]->setController(cntl_);
   }
   return(app_[dest]);
}

