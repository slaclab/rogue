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
rpr::ServerPtr rpr::Server::create (uint32_t segSize) {
   rpr::ServerPtr r = std::make_shared<rpr::Server>(segSize);
   return(r);
}

void rpr::Server::setup_python() {
#ifndef NO_PYTHON

   bp::class_<rpr::Server, rpr::ServerPtr, boost::noncopyable >("Server",bp::init<uint32_t>())
      .def("transport",        &rpr::Server::transport)
      .def("application",      &rpr::Server::application)
      .def("getOpen",          &rpr::Server::getOpen)
      .def("getDownCount",     &rpr::Server::getDownCount)
      .def("getDropCount",     &rpr::Server::getDropCount)
      .def("getRetranCount",   &rpr::Server::getRetranCount)
      .def("getLocBusy",       &rpr::Server::getLocBusy)
      .def("getLocBusyCnt",    &rpr::Server::getLocBusyCnt)
      .def("getRemBusy",       &rpr::Server::getRemBusy)
      .def("getRemBusyCnt",    &rpr::Server::getRemBusyCnt)
      .def("setLocTryPeriod",  &rpr::Server::setLocTryPeriod)
      .def("getLocTryPeriod",  &rpr::Server::getLocTryPeriod)
      .def("setLocMaxBuffers", &rpr::Server::setLocMaxBuffers)
      .def("getLocMaxBuffers", &rpr::Server::getLocMaxBuffers)
      .def("setLocMaxSegment", &rpr::Server::setLocMaxSegment)
      .def("getLocMaxSegment", &rpr::Server::getLocMaxSegment)
      .def("setLocCumAckTout", &rpr::Server::setLocCumAckTout)
      .def("getLocCumAckTout", &rpr::Server::getLocCumAckTout)
      .def("setLocRetranTout", &rpr::Server::setLocRetranTout)
      .def("getLocRetranTout", &rpr::Server::getLocRetranTout)
      .def("setLocNullTout",   &rpr::Server::setLocNullTout)
      .def("getLocNullTout",   &rpr::Server::getLocNullTout)
      .def("setLocMaxRetran",  &rpr::Server::setLocMaxRetran)
      .def("getLocMaxRetran",  &rpr::Server::getLocMaxRetran)
      .def("setLocMaxCumAck",  &rpr::Server::setLocMaxCumAck)
      .def("getLocMaxCumAck",  &rpr::Server::getLocMaxCumAck)
      .def("curMaxBuffers",    &rpr::Server::curMaxBuffers)
      .def("curMaxSegment",    &rpr::Server::curMaxSegment)
      .def("curCumAckTout",    &rpr::Server::curCumAckTout)
      .def("curRetranTout",    &rpr::Server::curRetranTout)
      .def("curNullTout",      &rpr::Server::curNullTout)
      .def("curMaxRetran",     &rpr::Server::curMaxRetran)
      .def("curMaxCumAck",     &rpr::Server::curMaxCumAck)
      .def("setTimeout",       &rpr::Server::setTimeout)
      .def("_stop",            &rpr::Server::stop)
      .def("_start",           &rpr::Server::start)
   ;
#endif
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

//! Get Retransmit Count
uint32_t rpr::Server::getRetranCount() {
   return(cntl_->getRetranCount());
}

//! Get locBusy
bool rpr::Server::getLocBusy() {
   return(cntl_->getLocBusy());
}

//! Get locBusyCnt
uint32_t rpr::Server::getLocBusyCnt() {
   return(cntl_->getLocBusyCnt());
}

//! Get remBusy
bool rpr::Server::getRemBusy() {
   return(cntl_->getRemBusy());
}

//! Get remBusyCnt
uint32_t rpr::Server::getRemBusyCnt() {
   return(cntl_->getRemBusyCnt());
}

void rpr::Server::setLocTryPeriod(uint32_t val) {
   cntl_->setLocTryPeriod(val);
}

uint32_t rpr::Server::getLocTryPeriod() {
   return cntl_->getLocTryPeriod();
}

void rpr::Server::setLocMaxBuffers(uint8_t val) {
   cntl_->setLocMaxBuffers(val);
}

uint8_t rpr::Server::getLocMaxBuffers() {
   return cntl_->getLocMaxBuffers();
}

void rpr::Server::setLocMaxSegment(uint16_t val) {
   cntl_->setLocMaxSegment(val);
}

uint16_t rpr::Server::getLocMaxSegment() {
   return cntl_->getLocMaxSegment();
}

void rpr::Server::setLocCumAckTout(uint16_t val) {
   cntl_->setLocCumAckTout(val);
}

uint16_t rpr::Server::getLocCumAckTout() {
   return cntl_->getLocCumAckTout();
}

void rpr::Server::setLocRetranTout(uint16_t val) {
   cntl_->setLocRetranTout(val);
}

uint16_t rpr::Server::getLocRetranTout() {
   return cntl_->getLocRetranTout();
}

void rpr::Server::setLocNullTout(uint16_t val) {
   cntl_->setLocNullTout(val);
}

uint16_t rpr::Server::getLocNullTout() {
   return cntl_->getLocNullTout();
}

void rpr::Server::setLocMaxRetran(uint8_t val) {
   cntl_->setLocMaxRetran(val);
}

uint8_t rpr::Server::getLocMaxRetran() {
   return cntl_->getLocMaxRetran();
}

void rpr::Server::setLocMaxCumAck(uint8_t val) {
   cntl_->setLocMaxCumAck(val);
}

uint8_t  rpr::Server::getLocMaxCumAck() {
   return cntl_->getLocMaxCumAck();
}

uint8_t  rpr::Server::curMaxBuffers() {
   return cntl_->curMaxBuffers();
}

uint16_t rpr::Server::curMaxSegment() {
   return cntl_->curMaxSegment();
}

uint16_t rpr::Server::curCumAckTout() {
   return cntl_->curCumAckTout();
}

uint16_t rpr::Server::curRetranTout() {
   return cntl_->curRetranTout();
}

uint16_t rpr::Server::curNullTout() {
   return cntl_->curNullTout();
}

uint8_t  rpr::Server::curMaxRetran() {
   return cntl_->curMaxRetran();
}

uint8_t  rpr::Server::curMaxCumAck() {
   return cntl_->curMaxCumAck();
}

//! Set timeout for frame transmits in microseconds
void rpr::Server::setTimeout(uint32_t timeout) {
   cntl_->setTimeout(timeout);
}

//! Send reset and close
void rpr::Server::stop() {
   return(cntl_->stop());
}

//! Start
void rpr::Server::start() {
   return(cntl_->start());
}

