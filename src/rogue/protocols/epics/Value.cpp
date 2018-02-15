/**
 *-----------------------------------------------------------------------------
 * Title      : EPICs PV Attribute Object
 * ----------------------------------------------------------------------------
 * File       : Value.cpp
 * Created    : 2018-11-18
 * ----------------------------------------------------------------------------
 * Description:
 * Class to store an EPICs PV attributes along with its current value
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
#include <rogue/protocols/epics/Value.h>
#include <rogue/protocols/epics/Pv.h>
#include <rogue/protocols/epics/Server.h>
#include <boost/make_shared.hpp>
#include <boost/make_shared.hpp>
#include <aitTypes.h>

namespace rpe = rogue::protocols::epics;
namespace bp  = boost::python;

//! Setup class in python
void rpe::Value::setup_python() {
   bp::class_<rpe::Value, rpe::ValuePtr, boost::noncopyable >("Value",bp::init<std::string>())
      .def("epicsName",      &rpe::Value::epicsName)
   ;
}

//! Class creation
rpe::Value::Value (std::string epicsName) {
   epicsName_ = epicsName;
   typeStr_   = "";
   //epicsType_ = aitUint8;
   pValue_    = NULL;
   pv_        = NULL;

   units_         = "";
   precision_     = 0;
   hopr_          = 0;
   lopr_          = 0;
   highAlarm_     = 0;
   highWarning_   = 0;
   lowWarning_    = 0;
   lowAlarm_      = 0;
   highCtrlLimit_ = 0;
   lowCtrlLimit_  = 0;

   // Populate function table
   funcTable_.installReadFunc("status",           &rpe::Value::readStatus);
   funcTable_.installReadFunc("severity",         &rpe::Value::readSeverity);
   funcTable_.installReadFunc("precision",        &rpe::Value::readPrecision);
   funcTable_.installReadFunc("alarmHigh",        &rpe::Value::readHighAlarm);
   funcTable_.installReadFunc("alarmHighWarning", &rpe::Value::readHighWarn);
   funcTable_.installReadFunc("alarmLowWarning",  &rpe::Value::readLowWarn);
   funcTable_.installReadFunc("alarmLow",         &rpe::Value::readLowAlarm);
   funcTable_.installReadFunc("value",            &rpe::Value::readValue);
   funcTable_.installReadFunc("graphicHigh",      &rpe::Value::readHopr);
   funcTable_.installReadFunc("graphicLow",       &rpe::Value::readLopr);
   funcTable_.installReadFunc("controlHigh",      &rpe::Value::readHighCtrl);
   funcTable_.installReadFunc("controlLow",       &rpe::Value::readLowCtrl);
   funcTable_.installReadFunc("units",            &rpe::Value::readUnits);
}

void rpe::Value::setType ( std::string typeStr ) {
   typeStr_ = typeStr;

   // Determine epics type
   //if      ( typeStr == "UInt8"   ) epicsType_ = aitUint8;
   //else if ( typeStr == "UInt16"  ) epicsType_ = aitUint16;
   //else if ( typeStr == "UInt32"  ) epicsType_ = aitUint32;
   //else if ( typeStr == "UInt64"  ) epicsType_ = aitUint64;
   //else if ( typeStr == "Int8"    ) epicsType_ = aitInt8;
   //else if ( typeStr == "Int16"   ) epicsType_ = aitInt16;
   //else if ( typeStr == "Int32"   ) epicsType_ = aitInt32;
   //else if ( typeStr == "Int64"   ) epicsType_ = aitInt64;
   //else if ( typeStr == "Float32" ) epicsType_ = aitFloat32;
   //else if ( typeStr == "Float64" ) epicsType_ = aitFloat64;
   //else if ( typeStr == "Bool"    ) epicsType_ = aitInt8;
   //else {
         // Throw an exception
   //}
}

std::string rpe::Value::epicsName() {
   return(epicsName_);
}

void rpe::Value::valueSet() { }

void rpe::Value::setPv(rpe::Pv * pv) {
   boost::lock_guard<boost::mutex> lock(mtx_);
   pv_ = pv;
}

void rpe::Value::clrPv() {
   boost::lock_guard<boost::mutex> lock(mtx_);
   pv_ = NULL;
}

rpe::Pv * rpe::Value::getPv() {
   boost::lock_guard<boost::mutex> lock(mtx_);
   return pv_;
}

//---------------------------------------
// EPICS Interface
//---------------------------------------
caStatus rpe::Value::read(gdd &prototype) {
   return funcTable_.read(*this, prototype);
}

caStatus rpe::Value::readValue(gdd &value) {
   double currentVal;

   pValue_->getConvert(currentVal);
   value.putConvert(currentVal);
   return S_casApp_success;
}

caStatus rpe::Value::write(gdd &value) {
   struct timespec t;
   double newVal;

   boost::lock_guard<boost::mutex> lock(mtx_);
   printf("Write called\n");

   clock_gettime(CLOCK_REALTIME,&t);

   caServer *pServer = pv_->getCAS();

   //// Doesn't support writing to arrays or container objects
   //// (gddAtomic or gddContainer).
   if(!(value.isScalar()) || !pServer) return S_casApp_noSupport;

   pValue_->unreference();
   pValue_ = &value;
   pValue_->reference();

   // Set the timespec structure to the current time stamp the gdd.
   pValue_->setTimeStamp(&t);
 
   // Get the new value and set the severity and status according to its value.
   value.get(newVal);

   this->valueSet();
   this->updated();
   return S_casApp_success;
}

void rpe::Value::updated() {
   boost::lock_guard<boost::mutex> lock(mtx_);
   if ( pv_ != NULL && pv_->interest() == aitTrue ) {
      caServer *pServer = pv_->getCAS();
      casEventMask select(pServer->valueEventMask() | pServer->alarmEventMask());
      pv_->postEvent(select, *pValue_);
   }
}

aitEnum rpe::Value::bestExternalType() {
   return pValue_->primitiveType();
}

gddAppFuncTableStatus rpe::Value::readStatus(gdd &value) {
   boost::lock_guard<boost::mutex> lock(mtx_);
   value.putConvert(pValue_->getStat());
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::Value::readSeverity(gdd &value) {
   boost::lock_guard<boost::mutex> lock(mtx_);
   value.putConvert(pValue_->getSevr());
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::Value::readPrecision(gdd &value) {
   value.putConvert(precision_);
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::Value::readHopr(gdd &value) {
   value.putConvert(hopr_);
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::Value::readLopr(gdd &value) {
   value.putConvert(lopr_);
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::Value::readHighAlarm(gdd &value) {
   value.putConvert(highAlarm_);
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::Value::readHighWarn(gdd &value) {
   value.putConvert(highWarning_);
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::Value::readLowWarn(gdd &value) {
   value.putConvert(lowWarning_);
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::Value::readLowAlarm(gdd &value) {
   value.putConvert(lowAlarm_);
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::Value::readHighCtrl(gdd &value) {
   value.putConvert(highCtrlLimit_);
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::Value::readLowCtrl(gdd &value) {
   value.putConvert(lowCtrlLimit_);
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::Value::readUnits(gdd &value) {
   value.put(units_.c_str());
   return S_casApp_success;
}

