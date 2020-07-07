/**
 *-----------------------------------------------------------------------------
 * Title      : Packetizer Core Class
 * ----------------------------------------------------------------------------
 * File       : CoreV2.cpp
 * Created    : 2018-02-02
 * ----------------------------------------------------------------------------
 * Description:
 * Packetizer Core V2
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
#include <rogue/protocols/packetizer/CoreV2.h>
#include <rogue/protocols/packetizer/Transport.h>
#include <rogue/protocols/packetizer/Application.h>
#include <rogue/protocols/packetizer/ControllerV2.h>
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
rpp::CoreV2Ptr rpp::CoreV2::create (bool enIbCrc, bool enObCrc, bool enSsi) {
   rpp::CoreV2Ptr r = std::make_shared<rpp::CoreV2>(enIbCrc,enObCrc,enSsi);
   return(r);
}

void rpp::CoreV2::setup_python() {
#ifndef NO_PYTHON

   bp::class_<rpp::CoreV2, rpp::CoreV2Ptr, boost::noncopyable >("CoreV2",bp::init<bool,bool,bool>())
      .def("transport",      &rpp::CoreV2::transport)
      .def("application",    &rpp::CoreV2::application)
      .def("getDropCount",   &rpp::CoreV2::getDropCount)

   ;
#endif
}

//! Creator
rpp::CoreV2::CoreV2 (bool enIbCrc, bool enObCrc, bool enSsi) {
   tran_  = rpp::Transport::create();
   cntl_  = rpp::ControllerV2::create(enIbCrc,enObCrc,enSsi,tran_,app_);

   tran_->setController(cntl_);
}

//! Destructor
rpp::CoreV2::~CoreV2() {
   uint32_t x;

   tran_.reset();
   cntl_.reset();

   for(x=0; x < 256; x++) app_[x].reset();
}

//! Get transport interface
rpp::TransportPtr rpp::CoreV2::transport() {
   return(tran_);
}

//! Application module
rpp::ApplicationPtr rpp::CoreV2::application(uint8_t dest) {
   if ( ! app_[dest] ) {
      app_[dest] = rpp::Application::create(dest);
      app_[dest]->setController(cntl_);
   }
   return(app_[dest]);
}

//! Get drop count
uint32_t rpp::CoreV2::getDropCount() {
   return(cntl_->getDropCount());
}

void rpp::CoreV2::setTimeout(uint32_t timeout) {
   cntl_->setTimeout(timeout);
}

