/**
 *-----------------------------------------------------------------------------
 * Title      : EPICs Pv
 * ----------------------------------------------------------------------------
 * File       : Pv.cpp
 * Created    : 2018-02-12
 * ----------------------------------------------------------------------------
 * Description:
 * EPICS Pv For Rogue System
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
#include <rogue/protocols/epics/Pv.h>
#include <rogue/protocols/epics/Value.h>
#include <time.h>

namespace rpe = rogue::protocols::epics;
namespace bp  = boost::python;

//! Setup class in python
void rpe::Pv::setup_python() { }

//! Class creation
rpe::Pv::Pv (caServer &cas, rpe::ValuePtr value) : casPV(cas) {
   value_    = value;
   interest_ = aitFalse;
}

rpe::Pv::~Pv () {
   value_->clrPv();
}

const char * rpe::Pv::getName() const {
   return value_->epicsName().c_str();
}

caStatus rpe::Pv::interestRegister() {
   boost::lock_guard<boost::mutex> lock(mtx_);
   interest_ = aitTrue;
   return S_casApp_success;
}

void rpe::Pv::interestDelete() { 
   boost::lock_guard<boost::mutex> lock(mtx_);
   interest_ = aitFalse;
}

bool rpe::Pv::interest() {
   return interest_;
}

caStatus rpe::Pv::beginTransaction() {
   return S_casApp_success;
}

void rpe::Pv::endTransaction() { }

caStatus rpe::Pv::read(const casCtx &ctx, gdd &prototype) {
   return value_->read(prototype);
}

caStatus rpe::Pv::write(const casCtx &ctx, gdd &value) {
   return value_->write(value);
}

aitEnum rpe::Pv::bestExternalType() {
   return value_->bestExternalType();
}

