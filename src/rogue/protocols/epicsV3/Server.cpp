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
#include <rogue/protocols/epicsV3/Work.h>
#include <rogue/GilRelease.h>
#include <rogue/GeneralError.h>
#include <fdManager.h>

namespace rpe = rogue::protocols::epicsV3;

#include <boost/python.hpp>
namespace bp  = boost::python;

//! Setup class in python
void rpe::Server::setup_python() {

   bp::class_<rpe::Server, rpe::ServerPtr, boost::noncopyable >("Server",bp::init<uint32_t>())
      .def("addValue", &rpe::Server::addValue)
      .def("start",    &rpe::Server::start)
      .def("stop",     &rpe::Server::stop)
   ;
}

//! Class creation
rpe::Server::Server (uint32_t count) : caServer(), running_(false) { 
   workCnt_ = count;
   workers_ = (boost::thread **)malloc(workCnt_ * sizeof(boost::thread *));
}

rpe::Server::~Server() {
   std::map<std::string, rpe::ValuePtr>::iterator it;

   stop();

   for ( it = values_.begin(); it != values_.end(); ++it ) {
      delete it->second->getPv();
      it->second.reset();
   }
   values_.clear();
   free(workers_);
}

void rpe::Server::start() {
   uint32_t x;
   //this->setDebugLevel(10);
   thread_ = new boost::thread(boost::bind(&rpe::Server::runThread, this));

   for (x=0; x < workCnt_; x++) 
      workers_[x] = new boost::thread(boost::bind(&rpe::Server::runWorker, this));

   running_ = true;
}

void rpe::Server::stop() {
   uint32_t x;

   if (running_) {
      rogue::GilRelease noGil;

      for (x=0; x < workCnt_; x++) 
         workQueue_.push(boost::shared_ptr<rogue::protocols::epicsV3::Work>());
        // workQueue_.push(NULL);

      for (x=0; x < workCnt_; x++) {
         workers_[x]->interrupt();
         workers_[x]->join();
      }

      thread_->interrupt();
      thread_->join();
      running_ = false;
   }
}

void rpe::Server::addValue(rpe::ValuePtr value) {
   std::map<std::string, rpe::ValuePtr>::iterator it;
   rpe::Pv * pv;

   boost::lock_guard<boost::mutex> lock(mtx_);

   if ( (it = values_.find(value->epicsName())) == values_.end()) {
      pv = new Pv(this, value);
      value->setPv(pv);
      values_[value->epicsName()] = value;
   }
   else {
      throw rogue::GeneralError("Server::addValue","EPICs name already exists: " + value->epicsName());
   }
}

void rpe::Server::addWork(rpe::WorkPtr work) {
   workQueue_.push(work);
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

//! Work thread
void rpe::Server::runWorker() {
   rpe::WorkPtr work;

   try {
      while(1) {
         work = workQueue_.pop();
         if (work == NULL) break;
         work->execute();
         boost::this_thread::interruption_point();
      }
   } catch (boost::thread_interrupted&) { }
}

