/**
 *-----------------------------------------------------------------------------
 * Title      : EPICs Variable
 * ----------------------------------------------------------------------------
 * File       : Variable.cpp
 * Created    : 2018-02-12
 * ----------------------------------------------------------------------------
 * Description:
 * EPICS Variable For Rogue System
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
#include <rogue/protocols/epics/Variable.h>
#include <rogue/protocols/epics/PvAttr.h>
#include <time.h>

namespace rpe = rogue::protocols::epics;
namespace bp  = boost::python;

//! Setup class in python
void rpe::Variable::setup_python() { }

//! Class creation
rpe::Variable::Variable (caServer &cas, rpe::PvAttrPtr attr) : casPV(cas) {
   attr_     = attr;
   interest_ = aitFalse;
}

rpe::Variable::~Variable () {
   attr_->clrPv();
}

const char * rpe::Variable::getName() const {
   return attr_->epicsName().c_str();
}

caStatus rpe::Variable::interestRegister() {
   boost::lock_guard<boost::mutex> lock(mtx_);
   interest_ = aitTrue;
   return S_casApp_success;
}

void rpe::Variable::interestDelete() { 
   boost::lock_guard<boost::mutex> lock(mtx_);
   interest_ = aitFalse;
}

bool rpe::Variable::interest() {
   return interest_;
}

caStatus rpe::Variable::beginTransaction() {
   return S_casApp_success;
}

void rpe::Variable::endTransaction() { }

caStatus rpe::Variable::read(const casCtx &ctx, gdd &prototype) {
   return attr_->read(prototype);
}

caStatus rpe::Variable::write(const casCtx &ctx, gdd &value) {
   return attr_->write(value);
}

aitEnum rpe::Variable::bestExternalType() {
   return attr_->bestExternalType();
}

