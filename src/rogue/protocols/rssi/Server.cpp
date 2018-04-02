/**
 *-----------------------------------------------------------------------------
 * Title      : RSSI Server Class
 * ----------------------------------------------------------------------------
 * File       : Server.h
 * Created    : 2017-06-13
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
#include <rogue/protocols/rssi/Server.h>
#include <rogue/protocols/rssi/Transport.h>
#include <rogue/protocols/rssi/Application.h>
#include <rogue/protocols/rssi/Controller.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <rogue/GilRelease.h>

namespace rpr = rogue::protocols::rssi;
namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Class creation
rpr::ServerPtr rpr::Server::create (uint32_t segSize) {
   rpr::ServerPtr r = boost::make_shared<rpr::Server>(segSize);
   return(r);
}

void rpr::Server::setup_python() {

   bp::class_<rpr::Server, rpr::ServerPtr, boost::noncopyable >("Server",bp::init<uint32_t>())
      .def("transport",      &rpr::Server::transport)
      .def("application",    &rpr::Server::application)
      .def("getOpen",        &rpr::Server::getOpen)
      .def("getDownCount",   &rpr::Server::getDownCount)
      .def("getDropCount",   &rpr::Server::getDropCount)
      .def("getRetranCount", &rpr::Server::getRetranCount)
      .def("getBusy",        &rpr::Server::getBusy)
      .def("stop",           &rpr::Server::stop)
   ;

}

//! Creator
rpr::Server::Server (uint32_t segSize) {
   app_   = rpr::Application::create();
   tran_  = rpr::Transport::create();
   cntl_  = rpr::Controller::create(segSize,tran_,app_,true);

   app_->setController(cntl_);
   tran_->setController(cntl_);
}

//! Destructor
rpr::Server::~Server() { 
   cntl_->stop();
}

//! Get transport interface
rpr::TransportPtr rpr::Server::transport() {
   return(tran_);
}

//! Application module
rpr::ApplicationPtr rpr::Server::application() {
   return(app_);
}

//! Get state
bool rpr::Server::getOpen() {
   return(cntl_->getOpen());
}

//! Get Down Count
uint32_t rpr::Server::getDownCount() {
   return(cntl_->getDownCount());
}

//! Get Drop Count
uint32_t rpr::Server::getDropCount() {
   return(cntl_->getDropCount());
}

//! Get Retran Count
uint32_t rpr::Server::getRetranCount() {
   return(cntl_->getRetranCount());
}

//! Get busy
bool rpr::Server::getBusy() {
   return(cntl_->getBusy());
}

//! Set timeout for frame transmits in microseconds
void rpr::Server::setTimeout(uint32_t timeout) {
   cntl_->setTimeout(timeout);
}

//! Send reset
void rpr::Server::stop() {
   return(cntl_->stop());
}

