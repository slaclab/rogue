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
#include <boost/make_shared.hpp>

namespace rpe = rogue::protocols::epics;
namespace bp  = boost::python;

//! Class creation
rpe::VariablePtr rpe::Variable::create (caServer &cas, rpe::PvAttrPtr attr) {
   rpe::VariablePtr r = boost::make_shared<rpe::Variable>(cas,attr);
   return(r);
}

//! Setup class in python
void rpe::Variable::setup_python() {
}

//! Class creation
rpe::Variable::Variable (caServer &cas, rpe::PvAttrPtr attr) : casPV(cas) {
   attr_ = attr;
   interest_ = aitFalse;
}

const char * rpe::Variable::getName() const {

}

caStatus rpe::Variable::interestRegister() {
   interest_ = aitTrue;
   return S_casApp_success;
}

void rpe::Variable::interestDelete() { 
   interest_ = aitFalse;
}

caStatus rpe::Variable::beginTransaction() {

}

void rpe::Variable::endTransaction() {

}

caStatus rpe::Variable::read(const casCtx &ctx, gdd &prototype) {

}

caStatus rpe::Variable::write(const casCtx &ctx, gdd &value) {

}

aitEnum rpe::Variable::bestExternalType() {

}

gddAppFuncTableStatus rpe::Variable::readStatus(gdd &value) {

}

gddAppFuncTableStatus rpe::Variable::readSeverity(gdd &value) {

}

gddAppFuncTableStatus rpe::Variable::readPrecision(gdd &value) {

}

gddAppFuncTableStatus rpe::Variable::readHopr(gdd &value) {

}

gddAppFuncTableStatus rpe::Variable::readLopr(gdd &value) {

}

gddAppFuncTableStatus rpe::Variable::readHighAlarm(gdd &value) {

}

gddAppFuncTableStatus rpe::Variable::readHighWarn(gdd &value) {

}

gddAppFuncTableStatus rpe::Variable::readLowWarn(gdd &value) {

}

gddAppFuncTableStatus rpe::Variable::readLowAlarm(gdd &value) {

}

gddAppFuncTableStatus rpe::Variable::readHighCtrl(gdd &value) {

}

gddAppFuncTableStatus rpe::Variable::readLowCtrl(gdd &value) {

}

gddAppFuncTableStatus rpe::Variable::readValue(gdd &value) {

}

gddAppFuncTableStatus rpe::Variable::readUnits(gdd &value) {

}

