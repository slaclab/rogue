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
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <boost/make_shared.hpp>
#include <aitTypes.h>

namespace rpe = rogue::protocols::epics;
namespace bp  = boost::python;

//! Setup class in python
void rpe::Value::setup_python() {
   bp::class_<rpe::Value, rpe::ValuePtr, boost::noncopyable >("Value",bp::init<std::string>())
      .def("epicsName", &rpe::Value::epicsName)
   ;
}

//! Class creation
rpe::Value::Value (std::string epicsName) {

   epicsName_ = epicsName;
   pv_        = NULL;
   pValue_    = NULL;

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
   funcTable_.installReadFunc("enums",            &rpe::Value::readEnums);

   // Default, type
   this->initGdd("UInt32", false, 1);
 
   // Default value 
   pValue_->putConvert((uint32_t) 0);
}

void rpe::Value::initGdd(std::string typeStr, bool isEnum, uint32_t count) {
   precision_ = 0;
   typeStr_   = typeStr;

   // Scalar
   if ( count == 1 ) {

      // Enum type
      if ( isEnum ) epicsType_ = aitEnumEnum16;

      // Int types
      else if ( typeStr == "UInt8"   ) epicsType_ = aitEnumUint8;
      else if ( typeStr == "UInt16"  ) epicsType_ = aitEnumUint16;
      else if ( typeStr == "int"     ) epicsType_ = aitEnumInt32;
      else if ( typeStr == "UInt32"  ) epicsType_ = aitEnumUint32;
      else if ( typeStr == "UInt64"  ) epicsType_ = aitEnumUint32; // epicsType_ = aitEnumUint64;
      else if ( typeStr == "Int8"    ) epicsType_ = aitEnumInt8;
      else if ( typeStr == "Int16"   ) epicsType_ = aitEnumInt16;
      else if ( typeStr == "Int32"   ) epicsType_ = aitEnumInt32;
      else if ( typeStr == "Int64"   ) epicsType_ = aitEnumInt32;  //epicsType_ = aitEnumInt64;

      // String type
      else if ( typeStr == "str" ) {
         epicsType_ = aitEnumString;
         pValue_->setBound(0,0,400);
      }

      // 32-bit Float
      else if ( typeStr == "float" or typeStr == "Float32" ) {
         epicsType_ = aitEnumFloat32;
         precision_ = 32;
      }

      // 64-bit float
      else if ( typeStr == "Float64" ) {
         epicsType_ = aitEnumFloat64;
         precision_ = 64;
      }

      else throw rogue::GeneralError("Value::initGdd","Invalid Type String: " + typeStr);

      pValue_ = new gddScalar(gddAppType_value, epicsType_);
   }
   else throw rogue::GeneralError("Value::initGdd","Invalid Size");
}

// Value lock held when this is called
void rpe::Value::updated() {
   if ( pv_ != NULL && pv_->interest() == aitTrue ) {
      caServer *pServer = pv_->getCAS();
      casEventMask select(pServer->valueEventMask() | pServer->alarmEventMask());
      pv_->postEvent(select, *pValue_);
   }
}

uint32_t rpe::Value::revEnum(std::string val) {
   uint32_t i;

   for (i =0; i < enums_.size(); i++) {
      if ( enums_[i] == val ) return i;
   }
   return(0);
}

std::string rpe::Value::epicsName() {
   return(epicsName_);
}

// Value lock held when this is called
void rpe::Value::valueSet() { }

// Value lock held when this is called
void rpe::Value::valueGet() { }

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
   gddStatus gdds;

   boost::lock_guard<boost::mutex> lock(mtx_);

   // Call value get within lock
   valueGet();

   gdds = gddApplicationTypeTable::app_table.smartCopy(&value, pValue_);

   if (gdds) return S_cas_noConvert;   
   else return S_casApp_success;

}

caStatus rpe::Value::write(const gdd &value) {
   struct timespec t;

   boost::lock_guard<boost::mutex> lock(mtx_);

   //// Doesn't support writing to arrays or container objects
   //// (gddAtomic or gddContainer).
   caServer *pServer = pv_->getCAS();
   if(!(value.isScalar()) || !pServer) return S_casApp_noSupport;

   // Set the new value
   pValue_->put(&value);

   // Set the timespec structure to the current time stamp the gdd.
   clock_gettime(CLOCK_REALTIME,&t);
   pValue_->setTimeStamp(&t);

   // Cal value set and update within lock 
   this->valueSet();
   this->updated();
   return S_casApp_success;
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

gddAppFuncTableStatus rpe::Value::readEnums(gdd &value) {
   aitFixedString * str;
   rpe::FixedStringDestructor * pDes;

   uint32_t nstr;
   uint32_t i;

   if ( epicsType_ == aitEnumEnum16 ) {
      nstr = enums_.size();

      str = new aitFixedString[nstr];
      if (!str) {
         return S_casApp_noMemory;
      }

      pDes = new rpe::FixedStringDestructor;
      if (!pDes) {
         delete [] str;
         return S_casApp_noMemory;
      }

      for (i=0; i < nstr; i++) 
         strncpy(str[i].fixed_string, enums_[i].c_str(), sizeof(str[i].fixed_string));

      value.setDimension(1);
      value.setBound (0,0,nstr);
      value.putRef (str, pDes);
 
      return S_cas_success;
   }

   return S_cas_success;
}

void rpe::FixedStringDestructor::run ( void * pUntyped ) {
    aitFixedString *ps = (aitFixedString *) pUntyped;
    delete [] ps;
}

