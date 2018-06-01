/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue EPICS V3 Interface: Top Level Server
 * ----------------------------------------------------------------------------
 * File       : Server.cpp
 * Created    : 2018-02-12
 * ----------------------------------------------------------------------------
 * Description:
 * EPICS Server For Rogue System
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

#include <rogue/protocols/epicsV3/Server.h>
#include <rogue/protocols/epicsV3/Value.h>
#include <rogue/protocols/epicsV3/Pv.h>
#include <rogue/GilRelease.h>
#include <rogue/GeneralError.h>
#include <fdManager.h>

namespace rpe = rogue::protocols::epicsV3;

#include <boost/python.hpp>
namespace bp  = boost::python;

//! Setup class in python
void rpe::Server::setup_python() {

   bp::class_<rpe::Server, rpe::ServerPtr, boost::noncopyable >("Server",bp::init<>())
      .def("addValue", &rpe::Server::addValue)
      .def("start",    &rpe::Server::start)
      .def("stop",     &rpe::Server::stop)
   ;
}

//! Class creation
rpe::Server::Server () : caServer() { }

rpe::Server::~Server() {
   stop();
}

void rpe::Server::start() {
   //this->setDebugLevel(10);
   thread_ = new boost::thread(boost::bind(&rpe::Server::runThread, this));
}

void rpe::Server::stop() {
   rogue::GilRelease noGil;
   thread_->interrupt();
   thread_->join();
}

void rpe::Server::addValue(rpe::ValuePtr value) {
   std::map<std::string, rpe::ValuePtr>::iterator it;
   rpe::Pv * pv;
   
   boost::lock_guard<boost::mutex> lock(mtx_);

   if ( (it = values_.find(value->epicsName())) == values_.end()) {
      pv = new Pv(*this, value);
      value->setPv(pv);
      values_[value->epicsName()] = value;
   }
   else {
      throw rogue::GeneralError("Server::addValue","EPICs name already exists: " + value->epicsName());
   }
}

pvExistReturn rpe::Server::pvExistTest(const casCtx &ctx, const char *pvName) {
   boost::lock_guard<boost::mutex> lock(mtx_);

   std::map<std::string, rpe::ValuePtr>::iterator it;

   if ( (it = values_.find(pvName)) == values_.end()) {
      return pverDoesNotExistHere;
   }
   else {
      return pverExistsHere;
   }
}

pvCreateReturn rpe::Server::createPV(const casCtx &ctx, const char *pvName) {
   boost::lock_guard<boost::mutex> lock(mtx_);

   std::map<std::string, rpe::ValuePtr>::iterator it;

   if ( (it = values_.find(pvName)) == values_.end())
      return S_casApp_pvNotFound;

   return *(it->second->getPv());
}

pvAttachReturn rpe::Server::pvAttach(const casCtx &ctx, const char *pvName) {
   boost::lock_guard<boost::mutex> lock(mtx_);

   std::map<std::string, rpe::ValuePtr>::iterator it;
   rpe::Pv * pv;

   if ( (it = values_.find(pvName)) == values_.end())
      return S_casApp_pvNotFound;

   return *(it->second->getPv());
}

//! Run thread
void rpe::Server::runThread() {
   try {
      while(1) {
         fileDescriptorManager.process(0.01);
         boost::this_thread::interruption_point();
      }
   } catch (boost::thread_interrupted&) { }
}

