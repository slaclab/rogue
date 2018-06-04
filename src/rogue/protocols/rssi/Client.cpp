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
#include <rogue/GilRelease.h>

namespace rpr = rogue::protocols::rssi;
namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Class creation
rpr::ClientPtr rpr::Client::create (uint32_t segSize) {
   rpr::ClientPtr r = boost::make_shared<rpr::Client>(segSize);
   return(r);
}

void rpr::Client::setup_python() {
#ifndef NO_PYTHON

   bp::class_<rpr::Client, rpr::ClientPtr, boost::noncopyable >("Client",bp::init<uint32_t>())
      .def("transport",       &rpr::Client::transport)
      .def("application",     &rpr::Client::application)
      .def("getOpen",         &rpr::Client::getOpen)
      .def("getDownCount",    &rpr::Client::getDownCount)
      .def("getDropCount",    &rpr::Client::getDropCount)
      .def("getRetranCount",  &rpr::Client::getRetranCount)
      .def("getLocBusy",      &rpr::Client::getLocBusy)
      .def("getLocBusyCnt",   &rpr::Client::getLocBusyCnt)
      .def("getRemBusy",      &rpr::Client::getRemBusy)
      .def("getRemBusyCnt",   &rpr::Client::getRemBusyCnt)
      .def("stop",            &rpr::Client::stop)
      .def("getMaxRetran",    &rpr::Client::getMaxRetran)
      .def("getRemMaxBuffers",&rpr::Client::getRemMaxBuffers)
      .def("getRemMaxSegment",&rpr::Client::getRemMaxSegment)
      .def("getRetranTout",   &rpr::Client::getRetranTout)
      .def("getCumAckTout",   &rpr::Client::getCumAckTout)
      .def("getNullTout",     &rpr::Client::getNullTout)
      .def("getMaxCumAck",    &rpr::Client::getMaxCumAck)
      .def("getSegmentSize",  &rpr::Client::getSegmentSize)
   ;
#endif
}

//! Creator
rpr::Client::Client (uint32_t segSize) {
   app_   = rpr::Application::create();
   tran_  = rpr::Transport::create();
   cntl_  = rpr::Controller::create(segSize,tran_,app_,false);

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

//! Get locBusy
bool rpr::Client::getLocBusy() {
   return(cntl_->getLocBusy());
}

//! Get locBusyCnt
uint32_t rpr::Client::getLocBusyCnt() {
   return(cntl_->getLocBusyCnt());
}

//! Get remBusy
bool rpr::Client::getRemBusy() {
   return(cntl_->getRemBusy());
}

//! Get remBusyCnt
uint32_t rpr::Client::getRemBusyCnt() {
   return(cntl_->getRemBusyCnt());
}

//! Get maxRetran
uint32_t rpr::Client::getMaxRetran() {
   return(cntl_->getMaxRetran());
}

//! Get remMaxBuffers
uint32_t rpr::Client::getRemMaxBuffers() {
   return(cntl_->getRemMaxBuffers());
}

//! Get remMaxSegment
uint32_t rpr::Client::getRemMaxSegment() {
   return(cntl_->getRemMaxSegment());
}

//! Get retranTout
uint32_t rpr::Client::getRetranTout() {
   return(cntl_->getRetranTout());
}

//! Get cumAckTout
uint32_t rpr::Client::getCumAckTout() {
   return(cntl_->getCumAckTout());
}

//! Get nullTout
uint32_t rpr::Client::getNullTout() {
   return(cntl_->getNullTout());
}

//! Get maxCumAck
uint32_t rpr::Client::getMaxCumAck() {
   return(cntl_->getMaxCumAck());
}

//! Get segmentSize
uint32_t rpr::Client::getSegmentSize() {
   return(cntl_->getSegmentSize());
}

//! Set timeout for frame transmits in microseconds
void rpr::Client::setTimeout(uint32_t timeout) {
   cntl_->setTimeout(timeout);
}

//! Send reset
void rpr::Client::stop() {
   return(cntl_->stop());
}
