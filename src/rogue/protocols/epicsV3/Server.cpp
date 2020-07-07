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

#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;

//! Setup class in python
void rpe::Server::setup_python() {

   bp::class_<rpe::Server, rpe::ServerPtr, boost::noncopyable >("Server",bp::init<uint32_t>())
      .def("_addValue", &rpe::Server::addValue)
      .def("_start",    &rpe::Server::start)
      .def("_stop",     &rpe::Server::stop)
   ;
}

//! Class creation
rpe::Server::Server (uint32_t count) : caServer(), running_(false) {
   workCnt_ = count;
   workersEn_ = false;
   threadEn_  = false;

   if ( count > 0 ) workers_ = (std::thread **)malloc(workCnt_ * sizeof(std::thread *));
   else workers_ = NULL;

   log_ = rogue::Logging::create("epicsV3.Server");
}

rpe::Server::~Server() {
   std::map<std::string, rpe::ValuePtr>::iterator it;

   stop();

   for ( it = values_.begin(); it != values_.end(); ++it ) {
      delete it->second->getPv();
      it->second.reset();
   }
   values_.clear();

   if ( workers_ != NULL ) free(workers_);
}

void rpe::Server::start() {
   uint32_t x;
   //this->setDebugLevel(10);

   log_->info("Starting epics server with %i workers",workCnt_);

   threadEn_ = true;
   thread_ = new std::thread(&rpe::Server::runThread, this);

   // Set a thread name
#ifndef __MACH__
   pthread_setname_np( thread_->native_handle(), "EpicsV3Server" );
#endif

   if ( workCnt_ > 0 ) {
      workersEn_ = true;
      for (x=0; x < workCnt_; x++)
         workers_[x] = new std::thread(boost::bind(&rpe::Server::runWorker, this));
   }
   running_ = true;
}

void rpe::Server::stop() {
   uint32_t x;

   log_->info("Stopping epics server");

   if (running_) {
      rogue::GilRelease noGil;

      for (x=0; x < workCnt_; x++)
         workQueue_.push(std::shared_ptr<rogue::protocols::epicsV3::Work>());

      workersEn_ = false;
      for (x=0; x < workCnt_; x++) workers_[x]->join();

      threadEn_ = false;
      thread_->join();
      running_ = false;
   }
}

void rpe::Server::addValue(rpe::ValuePtr value) {
   std::map<std::string, rpe::ValuePtr>::iterator it;
   rpe::Pv * pv;

   std::lock_guard<std::mutex> lock(mtx_);

   if ( (it = values_.find(value->epicsName())) == values_.end()) {
      pv = new Pv(this, value);
      value->setPv(pv);
      values_[value->epicsName()] = value;
   }
   else {
      throw rogue::GeneralError("Server::addValue","EPICs name already exists: " + value->epicsName());
   }
}

bool rpe::Server::doAsync() {
   return workersEn_;
}

void rpe::Server::addWork(rpe::WorkPtr work) {
   workQueue_.push(work);
}

pvExistReturn rpe::Server::pvExistTest(const casCtx &ctx, const char *pvName) {
   std::lock_guard<std::mutex> lock(mtx_);

   std::map<std::string, rpe::ValuePtr>::iterator it;

   if ( (it = values_.find(pvName)) == values_.end()) {
      return pverDoesNotExistHere;
   }
   else {
      return pverExistsHere;
   }
}

pvCreateReturn rpe::Server::createPV(const casCtx &ctx, const char *pvName) {
   std::lock_guard<std::mutex> lock(mtx_);

   std::map<std::string, rpe::ValuePtr>::iterator it;

   if ( (it = values_.find(pvName)) == values_.end())
      return S_casApp_pvNotFound;

   return *(it->second->getPv());
}

pvAttachReturn rpe::Server::pvAttach(const casCtx &ctx, const char *pvName) {
   std::lock_guard<std::mutex> lock(mtx_);

   std::map<std::string, rpe::ValuePtr>::iterator it;
   rpe::Pv * pv;

   if ( (it = values_.find(pvName)) == values_.end())
      return S_casApp_pvNotFound;

   return *(it->second->getPv());
}

//! Run thread
void rpe::Server::runThread() {

   log_->info("Starting epics server thread");
   log_->logThreadId();

   while(threadEn_) {
      try{
         fileDescriptorManager.process(0.01);
      } catch (...) {
         log_->error("Caught exception in server thread");
      }
   }
   log_->info("Stopping epics server thread");
}

//! Work thread
void rpe::Server::runWorker() {
   rpe::WorkPtr work;

   log_->info("Starting epics worker thread");
   log_->logThreadId();

   while(workersEn_) {
      work = workQueue_.pop();
      if (work == NULL) break;
      try{
         work->execute();
      } catch (...) {
         log_->error("Caught exception in worker thread");
      }
   }
}

