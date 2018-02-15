/**
 *-----------------------------------------------------------------------------
 * Title      : EPICs PV Attribute Object
 * ----------------------------------------------------------------------------
 * File       : PvAttr.cpp
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
#include <rogue/protocols/epics/PvAttr.h>
#include <rogue/protocols/epics/Variable.h>
#include <rogue/protocols/epics/Server.h>
#include <boost/make_shared.hpp>
#include <boost/make_shared.hpp>

namespace rpe = rogue::protocols::epics;
namespace bp  = boost::python;

//! Class creation
rpe::PvAttrPtr rpe::PvAttr::create (std::string epicsName, std::string typeStr, uint32_t nelms) {
   rpe::PvAttrPtr r = boost::make_shared<rpe::PvAttr>(epicsName,typeStr,nelms);
   return(r);
}

//! Setup class in python
void rpe::PvAttr::setup_python() {

   bp::class_<rpe::PvAttr, rpe::PvAttrPtr, boost::noncopyable >("PvAttr",bp::init<std::string,std::string,uint32_t>())
      .def("create",         &rpe::PvAttr::create)
      .staticmethod("create")
      .def("epicsName",      &rpe::PvAttr::epicsName)
      .def("setUnits",       &rpe::PvAttr::setUnits)
      .def("setPrecision",   &rpe::PvAttr::setPrecision)
   ;

}

//! Class creation
rpe::PvAttr::PvAttr (std::string epicsName, std::string typeStr, uint32_t nelms) {
   epicsName_ = epicsName;
   nelms_     = nelms;

   typeStr_       = typeStr;

   units_         = "";
   precision_     = 32;
   hopr_          = 0;
   lopr_          = 0;
   highAlarm_     = 0;
   highWarning_   = 0;
   lowWarning_    = 0;
   lowAlarm_      = 0;
   highCtrlLimit_ = 0;
   lowCtrlLimit_  = 0;

   pv_ = NULL;

   // Populate function table
   funcTable_.installReadFunc("status",           &rpe::PvAttr::readStatus);
   funcTable_.installReadFunc("severity",         &rpe::PvAttr::readSeverity);
   funcTable_.installReadFunc("precision",        &rpe::PvAttr::readPrecision);
   funcTable_.installReadFunc("alarmHigh",        &rpe::PvAttr::readHighAlarm);
   funcTable_.installReadFunc("alarmHighWarning", &rpe::PvAttr::readHighWarn);
   funcTable_.installReadFunc("alarmLowWarning",  &rpe::PvAttr::readLowWarn);
   funcTable_.installReadFunc("alarmLow",         &rpe::PvAttr::readLowAlarm);
   funcTable_.installReadFunc("value",            &rpe::PvAttr::readValue);
   funcTable_.installReadFunc("graphicHigh",      &rpe::PvAttr::readHopr);
   funcTable_.installReadFunc("graphicLow",       &rpe::PvAttr::readLopr);
   funcTable_.installReadFunc("controlHigh",      &rpe::PvAttr::readHighCtrl);
   funcTable_.installReadFunc("controlLow",       &rpe::PvAttr::readLowCtrl);
   funcTable_.installReadFunc("units",            &rpe::PvAttr::readUnits);


   // Determine epics type
   switch ( typeStr_ ) {
      case "UInt8"   : epicsType_ = aitUint8;   break;
      case "UInt16"  : epicsType_ = aitUint16;  break;
      case "UInt32"  : epicsType_ = aitUint32;  break;
      case "UInt64"  : epicsType_ = aitUint64;  break;
      case "Int8"    : epicsType_ = aitInt8;    break;
      case "Int16"   : epicsType_ = aitInt16;   break;
      case "Int32"   : epicsType_ = aitInt32;   break;
      case "Int64"   : epicsType_ = aitInt64;   break;
      case "Float32" : epicsType_ = aitFloat32; break;
      case "Float64" : epicsType_ = aitFloat64; break;
      case "Bool"    : epicsType_ = aitInt8;    break;
      default:
         // Throw an exception
         break;
   }

   pValue_ = new gddScalar(gddAppType_value, aitEnumFloat64);
   gddScaler
   gddArray 
   gddEnumStringTable


}

std::string rpe::PvAttr::epicsName() {
   return(epicsName_);
}

void rpe::PvAttr::varUpdated(boost::python::object p) {

   if ( 

   uint32_t ret = bp::extract<uint32_t>(_root.attr("get")(path));


}

void rpe::PvAttr::setUnits(std::string units) {
   units_ = units;
}

void rpe::PvAttr::setPrecision(uint16_t precision) {
   precision_ = precision;
}

void rpe::PvAttr::setPv(rpe::Variable * pv) {
   boost::lock_guard<boost::mutex> lock(mtx_);
   pv_ = pv;
}

void rpe::PvAttr::clrPv() {
   boost::lock_guard<boost::mutex> lock(mtx_);
   pv_ = NULL;
}

rpe::Variable * rpe::PvAttr::getPv() {
   boost::lock_guard<boost::mutex> lock(mtx_);
   return pv_;
}

//---------------------------------------
// EPICS Interface
//---------------------------------------
caStatus rpe::PvAttr::read(gdd &prototype) {
   printf("Read called for %s\n",epicsName_.c_str());
   return funcTable_.read(*this, prototype);
}

caStatus rpe::PvAttr::readValue(gdd &value) {
   printf("Read value for %s\n",epicsName_.c_str());
   double currentVal;

   pValue_->getConvert(currentVal);
   value.putConvert(currentVal);
   return S_casApp_success;
}

caStatus rpe::PvAttr::write(gdd &value) {
   printf("New value set for %s\n",epicsName_.c_str());

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

   this->updated();
   return S_casApp_success;
}

void rpe::PvAttr::updated() {
   boost::lock_guard<boost::mutex> lock(mtx_);
   if ( pv_ != NULL && pv_->interest() == aitTrue ) {
      caServer *pServer = pv_->getCAS();
      casEventMask select(pServer->valueEventMask() | pServer->alarmEventMask());
      pv_->postEvent(select, *pValue_);
   }
}

aitEnum rpe::PvAttr::bestExternalType() {
   printf("Type called %s\n",epicsName_.c_str());
   return pValue_->primitiveType();
}

gddAppFuncTableStatus rpe::PvAttr::readStatus(gdd &value) {
   boost::lock_guard<boost::mutex> lock(mtx_);
   value.putConvert(pValue_->getStat());
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::PvAttr::readSeverity(gdd &value) {
   boost::lock_guard<boost::mutex> lock(mtx_);
   value.putConvert(pValue_->getSevr());
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::PvAttr::readPrecision(gdd &value) {
   value.putConvert(precision_);
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::PvAttr::readHopr(gdd &value) {
   value.putConvert(hopr_);
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::PvAttr::readLopr(gdd &value) {
   value.putConvert(lopr_);
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::PvAttr::readHighAlarm(gdd &value) {
   value.putConvert(highAlarm_);
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::PvAttr::readHighWarn(gdd &value) {
   value.putConvert(highWarning_);
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::PvAttr::readLowWarn(gdd &value) {
   value.putConvert(lowWarning_);
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::PvAttr::readLowAlarm(gdd &value) {
   value.putConvert(lowAlarm_);
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::PvAttr::readHighCtrl(gdd &value) {
   value.putConvert(highCtrlLimit_);
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::PvAttr::readLowCtrl(gdd &value) {
   value.putConvert(lowCtrlLimit_);
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::PvAttr::readUnits(gdd &value) {
   value.put(units_.c_str());
   return S_casApp_success;
}

