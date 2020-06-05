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
#include <rogue/protocols/packetizer/ControllerV1.h>
#include <rogue/GeneralError.h>
#include <memory>
#include <rogue/GilRelease.h>

namespace rpp = rogue::protocols::packetizer;
namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Class creation
rpp::CorePtr rpp::Core::create (bool enSsi) {
   rpp::CorePtr r = std::make_shared<rpp::Core>(enSsi);
   return(r);
}

void rpp::Core::setup_python() {
#ifndef NO_PYTHON

   bp::class_<rpp::Core, rpp::CorePtr, boost::noncopyable >("Core",bp::init<bool>())
      .def("transport",      &rpp::Core::transport)
      .def("application",    &rpp::Core::application)
      .def("getDropCount",   &rpp::Core::getDropCount)

   ;
#endif
}

//! Creator
rpp::Core::Core (bool enSsi) {
   tran_  = rpp::Transport::create();
   cntl_  = rpp::ControllerV1::create(enSsi,tran_,app_);

   tran_->setController(cntl_);
}

//! Destructor
rpp::Core::~Core() {
   uint32_t x;

   tran_.reset();
   cntl_.reset();

   for(x=0; x < 256; x++) app_[x].reset();
}

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

//! Get drop count
uint32_t rpp::Core::getDropCount() {
   return(cntl_->getDropCount());
}

void rpp::Core::setTimeout(uint32_t timeout) {
   cntl_->setTimeout(timeout);
}

