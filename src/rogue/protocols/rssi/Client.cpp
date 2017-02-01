/**
 *-----------------------------------------------------------------------------
 * Title      : RSSI Client Class
 * ----------------------------------------------------------------------------
 * File       : Client.h
 * Created    : 2017-01-07
 * Last update: 2017-01-07
 * ----------------------------------------------------------------------------
 * Description:
 * UDP Client
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
#include <rogue/protocols/rssi/Client.h>
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
rpr::ClientPtr rpr::Client::create (uint32_t segSize) {
   rpr::ClientPtr r = boost::make_shared<rpr::Client>(segSize);
   return(r);
}

void rpr::Client::setup_python() {

   bp::class_<rpr::Client, rpr::ClientPtr, boost::noncopyable >("Client",bp::init<uint32_t>())
      .def("create",         &rpr::Client::create)
      .staticmethod("create")
      .def("transport",      &rpr::Client::transport)
      .def("application",    &rpr::Client::application)
      .def("getOpen",        &rpr::Client::getOpen)
      .def("getDownCount",   &rpr::Client::getDownCount)
      .def("getDropCount",   &rpr::Client::getDropCount)
      .def("getRetranCount", &rpr::Client::getRetranCount)
      .def("getBusy",        &rpr::Client::getBusy)
   ;

}

//! Creator
rpr::Client::Client (uint32_t segSize) {
   app_   = rpr::Application::create();
   tran_  = rpr::Transport::create();
   cntl_  = rpr::Controller::create(segSize,tran_,app_);

   app_->setController(cntl_);
   tran_->setController(cntl_);
}

//! Destructor
rpr::Client::~Client() { 
   cntl_->stop();
}

//! Get transport interface
rpr::TransportPtr rpr::Client::transport() {
   return(tran_);
}

//! Application module
rpr::ApplicationPtr rpr::Client::application() {
   return(app_);
}

//! Get state
bool rpr::Client::getOpen() {
   return(cntl_->getOpen());
}

//! Get Down Count
uint32_t rpr::Client::getDownCount() {
   return(cntl_->getDownCount());
}

//! Get Drop Count
uint32_t rpr::Client::getDropCount() {
   return(cntl_->getDropCount());
}

//! Get Retran Count
uint32_t rpr::Client::getRetranCount() {
   return(cntl_->getRetranCount());
}

//! Get busy
bool rpr::Client::getBusy() {
   return(cntl_->getBusy());
}

//! Set timeout for frame transmits in microseconds
void rpr::Client::setTimeout(uint32_t timeout) {
   cntl_->setTimeout(timeout);
}

