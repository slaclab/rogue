/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue EPICS V3 Interface: PV Interface
 * ----------------------------------------------------------------------------
 * File       : Pv.cpp
 * Created    : 2018-02-12
 * ----------------------------------------------------------------------------
 * Description:
 * EPICS Pv For Rogue System, dynamically created and deleted as clients attach
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

#include <rogue/protocols/epicsV3/Pv.h>
#include <rogue/protocols/epicsV3/Value.h>
#include <rogue/protocols/epicsV3/Server.h>
#include <rogue/protocols/epicsV3/Work.h>
#include <time.h>

namespace rpe = rogue::protocols::epicsV3;

#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;

//! Class creation
rpe::Pv::Pv (rpe::Server *server, rpe::ValuePtr value) : casPV(*server) {
   value_    = value;
   interest_ = aitFalse;
   server_   = server;

//   valueMask_ = casEventMask(this->getCAS()->valueEventMask());
}

rpe::Pv::~Pv () { }

void rpe::Pv::show(unsigned level) const { }

caStatus rpe::Pv::interestRegister() {
   std::lock_guard<std::mutex> lock(mtx_);
   interest_ = aitTrue;
   valueMask_ = casEventMask(this->getCAS()->valueEventMask());
   return S_casApp_success;
}

void rpe::Pv::interestDelete() {
   std::lock_guard<std::mutex> lock(mtx_);
   interest_ = aitFalse;
}

caStatus rpe::Pv::beginTransaction() {
   return S_casApp_success;
}

void rpe::Pv::endTransaction() { }

caStatus rpe::Pv::read(const casCtx &ctx, gdd &value) {
   if (server_->doAsync()) {
      casAsyncReadIO * rio = new casAsyncReadIO(ctx);
      rpe::WorkPtr work = rpe::Work::createRead(value_, value, rio);
      server_->addWork(work);
      return S_casApp_asyncCompletion;
   }
   else return value_->read(value);
}

caStatus rpe::Pv::write(const casCtx &ctx, const gdd &value) {
   if (server_->doAsync()) {
      casAsyncWriteIO * wio = new casAsyncWriteIO(ctx);
      rpe::WorkPtr work = rpe::Work::createWrite(value_, value, wio);
      server_->addWork(work);
      return S_casApp_asyncCompletion;
   }
   else return value_->write(value);
}

caStatus rpe::Pv::writeNotify(const casCtx &ctx, const gdd &value) {
   if (server_->doAsync()) {
      casAsyncWriteIO * wio = new casAsyncWriteIO(ctx);
      rpe::WorkPtr work = rpe::Work::createWrite(value_, value, wio);
      server_->addWork(work);
      return S_casApp_asyncCompletion;
   }
   else return value_->write(value);
}

casChannel * rpe::Pv::createChannel(const casCtx &ctx,
                                    const char * const pUserName,
                                    const char * const pHostName) {

   return casPV::createChannel(ctx,pUserName,pHostName);
}

void rpe::Pv::destroy() {
   // Do nothing since we pre-allocate
}

aitEnum rpe::Pv::bestExternalType() const {
   return value_->bestExternalType();
}

unsigned rpe::Pv::maxDimension() const {
   return value_->maxDimension();
}

aitIndex rpe::Pv::maxBound(unsigned dimension) const {
   return value_->maxBound(dimension);
}

const char * rpe::Pv::getName() const {
   return value_->epicsName().c_str();
}

void rpe::Pv::updated ( const gdd & event ) {
   if ( interest_ == aitTrue ) casPV::postEvent(valueMask_,event);
}

