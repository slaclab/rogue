/**
 *-----------------------------------------------------------------------------
 * Title      : EPICs Epics Server
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

#include <boost/python.hpp>
#include <rogue/protocols/epics/Server.h>
#include <rogue/protocols/epics/PvAttr.h>
#include <rogue/protocols/epics/Variable.h>
#include <rogue/GilRelease.h>
#include <fdManager.h>

namespace rpe = rogue::protocols::epics;
namespace bp  = boost::python;

//! Setup class in python
void rpe::Server::setup_python() {

   bp::class_<rpe::Server, rpe::ServerPtr, boost::noncopyable >("Server",bp::init<>())
      .def("addVariable",    &rpe::Server::addVariable)
   ;
}

//! Class creation
rpe::Server::Server () : caServer() {
   thread_ = new boost::thread(boost::bind(&rpe::Server::runThread, this));
}

rpe::Server::~Server() {
   rogue::GilRelease noGil;
   thread_->interrupt();
   thread_->join();
}

void rpe::Server::addVariable(rpe::PvAttrPtr var) {
   boost::lock_guard<boost::mutex> lock(mtx_);

   pvByEpicsName_[var->epicsName()] = var;
}

pvExistReturn rpe::Server::pvExistTest(const casCtx &ctx, const char *pvName) {
   boost::lock_guard<boost::mutex> lock(mtx_);

   std::map<std::string, rpe::PvAttrPtr>::iterator it;

   if ( (it = pvByEpicsName_.find(pvName)) == pvByEpicsName_.end()) {
      return pverDoesNotExistHere;
   }
   else {
      return pverExistsHere;
   }
}

pvCreateReturn rpe::Server::createPV(const casCtx &ctx, const char *pvName) {
   boost::lock_guard<boost::mutex> lock(mtx_);

   std::map<std::string, rpe::PvAttrPtr>::iterator it;
   rpe::Variable * pv;

   if ( (it = pvByEpicsName_.find(pvName)) == pvByEpicsName_.end())
      return S_casApp_pvNotFound;

   if ( (pv = it->second->getPv()) == NULL ) {
      pv = new Variable(*this, it->second);
      it->second->setPv(pv);
   }

   return *pv;
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

