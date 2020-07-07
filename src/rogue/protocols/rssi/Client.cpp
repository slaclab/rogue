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
#include <memory>
#include <rogue/GilRelease.h>

namespace rpr = rogue::protocols::rssi;
namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Class creation
rpr::ClientPtr rpr::Client::create (uint32_t segSize) {
   rpr::ClientPtr r = std::make_shared<rpr::Client>(segSize);
   return(r);
}

void rpr::Client::setup_python() {
#ifndef NO_PYTHON

   bp::class_<rpr::Client, rpr::ClientPtr, boost::noncopyable >("Client",bp::init<uint32_t>())
      .def("transport",        &rpr::Client::transport)
      .def("application",      &rpr::Client::application)
      .def("getOpen",          &rpr::Client::getOpen)
      .def("getDownCount",     &rpr::Client::getDownCount)
      .def("getDropCount",     &rpr::Client::getDropCount)
      .def("getRetranCount",   &rpr::Client::getRetranCount)
      .def("getLocBusy",       &rpr::Client::getLocBusy)
      .def("getLocBusyCnt",    &rpr::Client::getLocBusyCnt)
      .def("getRemBusy",       &rpr::Client::getRemBusy)
      .def("getRemBusyCnt",    &rpr::Client::getRemBusyCnt)
      .def("setLocTryPeriod",  &rpr::Client::setLocTryPeriod)
      .def("getLocTryPeriod",  &rpr::Client::getLocTryPeriod)
      .def("setLocMaxBuffers", &rpr::Client::setLocMaxBuffers)
      .def("getLocMaxBuffers", &rpr::Client::getLocMaxBuffers)
      .def("setLocMaxSegment", &rpr::Client::setLocMaxSegment)
      .def("getLocMaxSegment", &rpr::Client::getLocMaxSegment)
      .def("setLocCumAckTout", &rpr::Client::setLocCumAckTout)
      .def("getLocCumAckTout", &rpr::Client::getLocCumAckTout)
      .def("setLocRetranTout", &rpr::Client::setLocRetranTout)
      .def("getLocRetranTout", &rpr::Client::getLocRetranTout)
      .def("setLocNullTout",   &rpr::Client::setLocNullTout)
      .def("getLocNullTout",   &rpr::Client::getLocNullTout)
      .def("setLocMaxRetran",  &rpr::Client::setLocMaxRetran)
      .def("getLocMaxRetran",  &rpr::Client::getLocMaxRetran)
      .def("setLocMaxCumAck",  &rpr::Client::setLocMaxCumAck)
      .def("getLocMaxCumAck",  &rpr::Client::getLocMaxCumAck)
      .def("curMaxBuffers",    &rpr::Client::curMaxBuffers)
      .def("curMaxSegment",    &rpr::Client::curMaxSegment)
      .def("curCumAckTout",    &rpr::Client::curCumAckTout)
      .def("curRetranTout",    &rpr::Client::curRetranTout)
      .def("curNullTout",      &rpr::Client::curNullTout)
      .def("curMaxRetran",     &rpr::Client::curMaxRetran)
      .def("curMaxCumAck",     &rpr::Client::curMaxCumAck)
      .def("setTimeout",       &rpr::Client::setTimeout)
      .def("_stop",            &rpr::Client::stop)
      .def("_start",           &rpr::Client::start)
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

void rpr::Client::setLocTryPeriod(uint32_t val) {
   cntl_->setLocTryPeriod(val);
}

uint32_t rpr::Client::getLocTryPeriod() {
   return cntl_->getLocTryPeriod();
}

void rpr::Client::setLocMaxBuffers(uint8_t val) {
   cntl_->setLocMaxBuffers(val);
}

uint8_t rpr::Client::getLocMaxBuffers() {
   return cntl_->getLocMaxBuffers();
}

void rpr::Client::setLocMaxSegment(uint16_t val) {
   cntl_->setLocMaxSegment(val);
}

uint16_t rpr::Client::getLocMaxSegment() {
   return cntl_->getLocMaxSegment();
}

void rpr::Client::setLocCumAckTout(uint16_t val) {
   cntl_->setLocCumAckTout(val);
}

uint16_t rpr::Client::getLocCumAckTout() {
   return cntl_->getLocCumAckTout();
}

void rpr::Client::setLocRetranTout(uint16_t val) {
   cntl_->setLocRetranTout(val);
}

uint16_t rpr::Client::getLocRetranTout() {
   return cntl_->getLocRetranTout();
}

void rpr::Client::setLocNullTout(uint16_t val) {
   cntl_->setLocNullTout(val);
}

uint16_t rpr::Client::getLocNullTout() {
   return cntl_->getLocNullTout();
}

void rpr::Client::setLocMaxRetran(uint8_t val) {
   cntl_->setLocMaxRetran(val);
}

uint8_t rpr::Client::getLocMaxRetran() {
   return cntl_->getLocMaxRetran();
}

void rpr::Client::setLocMaxCumAck(uint8_t val) {
   cntl_->setLocMaxCumAck(val);
}

uint8_t  rpr::Client::getLocMaxCumAck() {
   return cntl_->getLocMaxCumAck();
}

uint8_t  rpr::Client::curMaxBuffers() {
   return cntl_->curMaxBuffers();
}

uint16_t rpr::Client::curMaxSegment() {
   return cntl_->curMaxSegment();
}

uint16_t rpr::Client::curCumAckTout() {
   return cntl_->curCumAckTout();
}

uint16_t rpr::Client::curRetranTout() {
   return cntl_->curRetranTout();
}

uint16_t rpr::Client::curNullTout() {
   return cntl_->curNullTout();
}

uint8_t  rpr::Client::curMaxRetran() {
   return cntl_->curMaxRetran();
}

uint8_t  rpr::Client::curMaxCumAck() {
   return cntl_->curMaxCumAck();
}

//! Set timeout for frame transmits in microseconds
void rpr::Client::setTimeout(uint32_t timeout) {
   cntl_->setTimeout(timeout);
}

//! Send reset and close
void rpr::Client::stop() {
   return(cntl_->stop());
}

//! Start
void rpr::Client::start() {
   return(cntl_->start());
}

