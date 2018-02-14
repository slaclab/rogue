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
#include <time.h>

namespace rpe = rogue::protocols::epics;
namespace bp  = boost::python;

//! Class creation
rpe::VariablePtr rpe::Variable::create (caServer &cas, rpe::PvAttrPtr attr) {
   rpe::VariablePtr r = boost::make_shared<rpe::Variable>(cas,attr);
   return(r);
}

//! Setup class in python
void rpe::Variable::setup_python() { }

//! Class creation
rpe::Variable::Variable (caServer &cas, rpe::PvAttrPtr attr) : casPV(cas) {
   attr_ = attr;
   interest_ = aitFalse;

   // Populate function table
   funcTable_.installReadFunc("status",           &rpe::Variable::readStatus);
   funcTable_.installReadFunc("severity",         &rpe::Variable::readSeverity);
   funcTable_.installReadFunc("precision",        &rpe::Variable::readPrecision);
   funcTable_.installReadFunc("alarmHigh",        &rpe::Variable::readHighAlarm);
   funcTable_.installReadFunc("alarmHighWarning", &rpe::Variable::readHighWarn);
   funcTable_.installReadFunc("alarmLowWarning",  &rpe::Variable::readLowWarn);
   funcTable_.installReadFunc("alarmLow",         &rpe::Variable::readLowAlarm);
   funcTable_.installReadFunc("value",            &rpe::Variable::readValue);
   funcTable_.installReadFunc("graphicHigh",      &rpe::Variable::readHopr);
   funcTable_.installReadFunc("graphicLow",       &rpe::Variable::readLopr);
   funcTable_.installReadFunc("controlHigh",      &rpe::Variable::readHighCtrl);
   funcTable_.installReadFunc("controlLow",       &rpe::Variable::readLowCtrl);
   funcTable_.installReadFunc("units",            &rpe::Variable::readUnits);

   double value; // The initial value of the PV.

   gdd *pValue = attr_->getVal(); // Get pointer to gdd object.
   if(!pValue) return;

   value = 10.0;

   pValue->putConvert(value);
}

const char * rpe::Variable::getName() const {
   return attr_->epicsName().c_str();
}

caStatus rpe::Variable::interestRegister() {
   interest_ = aitTrue;
   return S_casApp_success;
}

void rpe::Variable::interestDelete() { 
   interest_ = aitFalse;
}

caStatus rpe::Variable::beginTransaction() {
   return S_casApp_success;
}

void rpe::Variable::endTransaction() {

}

caStatus rpe::Variable::read(const casCtx &ctx, gdd &prototype) {
   return funcTable_.read(*this, prototype);
}

caStatus rpe::Variable::write(const casCtx &ctx, gdd &value) {
   struct timespec t;
   //struct timeval  t;
   gdd *pValue;
   double newVal;

   //gettimeofday(&t,NULL);
   //timespec_get(&t,0);

   caServer *pServer = this->getCAS();

   //// Doesn't support writing to arrays or container objects
   //// (gddAtomic or gddContainer).
   if(!(value.isScalar()) || !pServer) return S_casApp_noSupport;

   pValue = attr_->getVal();
   // If pValue exists, unreference it, set the pointer to the new gdd
   // object, and reference it.

   if(pValue) pValue->unreference();

   pValue = &value;
   pValue->reference();

   // Set the timespec structure to the current time stamp the gdd.
   pValue->setTimeStamp(&t);
 
   // Get the new value and set the severity and status according to its value.
   value.get(newVal);

   if(interest_ == aitTrue){
      casEventMask select(pServer->valueEventMask | pServer->alarmEventMask);
      postEvent(select, *pValue);
   }
   return S_casApp_success;
}

aitEnum rpe::Variable::bestExternalType() {
   gdd* pValue = attr_->getVal();
   if(!pValue)
      return aitEnumInvalid;
   else
      return pValue->primitiveType();
}

gddAppFuncTableStatus rpe::Variable::readStatus(gdd &value) {
   gdd *pValue = attr_->getVal();
   if(pValue)
      value.putConvert(pValue->getStat());
   else
      value.putConvert(epicsAlarmUDF);
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::Variable::readSeverity(gdd &value) {
   gdd *pValue = attr_->getVal();
   if(pValue)
      value.putConvert(pValue->getSevr());
   else
      value.putConvert(epicsSevNone);
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::Variable::readPrecision(gdd &value) {
   value.putConvert(attr_->getPrecision());
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::Variable::readHopr(gdd &value) {
   value.putConvert(attr_->getHopr());
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::Variable::readLopr(gdd &value) {
   value.putConvert(attr_->getLopr());
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::Variable::readHighAlarm(gdd &value) {
   value.putConvert(attr_->getHighAlarm());
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::Variable::readHighWarn(gdd &value) {
   value.putConvert(attr_->getHighWarning());
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::Variable::readLowWarn(gdd &value) {
   value.putConvert(attr_->getLowWarning());
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::Variable::readLowAlarm(gdd &value) {
   value.putConvert(attr_->getLowAlarm());
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::Variable::readHighCtrl(gdd &value) {
   value.putConvert(attr_->getHighCtrl());
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::Variable::readLowCtrl(gdd &value) {
   value.putConvert(attr_->getLowCtrl());
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::Variable::readValue(gdd &value) {
   double currentVal;
   gdd *pValue = attr_->getVal();

   if(!pValue)
      return S_casApp_undefined;
   else {
      pValue->getConvert(currentVal);
      value.putConvert(currentVal);
      return S_casApp_success;
   }
}

gddAppFuncTableStatus rpe::Variable::readUnits(gdd &value) {
   value.put(attr_->getUnits().c_str());
   return S_casApp_success;
}

