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
#include <boost/make_shared.hpp>
#include <rogue/GilRelease.h>
#include <fdManager.h>

namespace rpe = rogue::protocols::epics;
namespace bp  = boost::python;

//! Class creation
rpe::ServerPtr rpe::Server::create (uint32_t countEstimate) {
   printf("Server create called\n");
   rpe::ServerPtr r = boost::make_shared<rpe::Server>(countEstimate);
   return(r);
}

//! Setup class in python
void rpe::Server::setup_python() {

   bp::class_<rpe::Server, rpe::ServerPtr, boost::noncopyable >("Server",bp::init<uint32_t>())
      .def("create",         &rpe::Server::create)
      .staticmethod("create")
      .def("addVariable",    &rpe::Server::addVariable)
   ;
}

//! Class creation
//rpe::Server::Server (uint32_t countEstimate) : caServer(countEstimate) {
rpe::Server::Server (uint32_t countEstimate) : caServer() {
   printf("Server created\n");
   thread_ = new boost::thread(boost::bind(&rpe::Server::runThread, this));
}

rpe::Server::~Server() {
   printf("Server destructor called\n");
   rogue::GilRelease noGil;
   thread_->interrupt();
   thread_->join();
}

void rpe::Server::addVariable(rpe::PvAttrPtr var) {
   pvByRoguePath_[var->roguePath()] = var;
   pvByEpicsName_[var->epicsName()] = var;

   printf("Creating epics variable %s\n",var->epicsName().c_str());

   var->setServer(shared_from_this());
}

pvExistReturn rpe::Server::pvExistTest(const casCtx &ctx, const char *pvName) {
   std::map<std::string, rpe::PvAttrPtr>::iterator it;

   printf("Looking for variable %s\n",pvName);

   if ( (it = pvByEpicsName_.find(pvName)) == pvByEpicsName_.end()) {
      printf("Did not find variable %s\n",pvName);
      return pverDoesNotExistHere;
   }
   else {
      printf("Found variable %s\n",pvName);
      return pverExistsHere;
   }
}

pvCreateReturn rpe::Server::createPV(const casCtx &ctx, const char *pvName) {
   std::map<std::string, rpe::PvAttrPtr>::iterator it;
   rpe::VariablePtr pv;

   if ( (it = pvByEpicsName_.find(pvName)) == pvByEpicsName_.end())
      return S_casApp_pvNotFound;

   if ( it->second->getPv() == NULL ) {
      pv = rpe::Variable::create(*this, it->second);
      it->second->setPv(pv);
   }

   printf("Created variable %s\n",pvName);

   return *pv;
}


//! Run thread
void rpe::Server::runThread() {
   try {
      printf("Entering server loop\n");
      while(1) {
         fileDescriptorManager.process(0.01);
      }
   } catch (boost::thread_interrupted&) { }
   printf("Exiting server loop\n");
}

