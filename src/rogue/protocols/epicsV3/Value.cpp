/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue EPICS V3 Interface: Generic Value Container
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

#include <rogue/protocols/epicsV3/Value.h>
#include <rogue/protocols/epicsV3/Pv.h>
#include <rogue/GeneralError.h>
#include <memory>
#include <memory>
#include <aitTypes.h>

#ifdef __MACH__
#include <mach/clock.h>
#include <mach/mach.h>
#endif

namespace rpe = rogue::protocols::epicsV3;

#include <boost/python.hpp>
namespace bp  = boost::python;

//! Setup class in python
void rpe::Value::setup_python() {
   bp::class_<rpe::Value, rpe::ValuePtr, boost::noncopyable >("Value",bp::no_init)
      .def("epicsName", &rpe::Value::epicsName)
   ;
}

//! Class creation
rpe::Value::Value (std::string epicsName) {
   epicsName_ = epicsName;
   pv_        = NULL;
   pValue_    = NULL;

   precision_ = 0;
   typeStr_   = "";
   size_      = 1;
   max_       = 1;
   fSize_     = 1;
   array_     = false;
   isString_  = false;
   epicsType_ = aitEnumInvalid;

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

   log_ = rogue::Logging::create("epicsV3.Value");

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
}

void rpe::Value::initGdd(std::string typeStr, bool isEnum, uint32_t count) {
   uint32_t bitSize;

   log_->info("Init GDD for %s typeStr=%s, isEnum=%i, count=%i",
         epicsName_.c_str(),typeStr.c_str(),isEnum,count);

   // Save current type
   typeStr_ = typeStr;

   // Enum type
   if ( isEnum ) {
      epicsType_ = aitEnumEnum16;
      log_->info("Detected enum for %s typeStr=%s", epicsName_.c_str(),typeStr.c_str());
   }

   // Unsigned Int types, > 32-bits treated as string
   else if ( sscanf(typeStr.c_str(),"UInt%i",&bitSize) == 1 ) {
      if ( bitSize <=  8 ) { fSize_ = 1; epicsType_ = aitEnumUint8; } 
      else if ( bitSize <= 16 ) { fSize_ = 2; epicsType_ = aitEnumUint16; } 
      else if ( bitSize <= 32) { fSize_ = 4; epicsType_ = aitEnumUint32; } 
      else { epicsType_ = aitEnumString; } 

      log_->info("Detected Rogue Uint with size %i for %s typeStr=%s",
            bitSize, epicsName_.c_str(),typeStr.c_str());
  }

   // Signed Int types, > 32-bits treated as string
   else if ( sscanf(typeStr.c_str(),"Int%i",&bitSize) == 1 ) {
      if ( bitSize <=  8 ) { fSize_ = 1; epicsType_ = aitEnumInt8; } 
      else if ( bitSize <= 16 ) { fSize_ = 2; epicsType_ = aitEnumInt16; } 
      else if ( bitSize <= 32 ) { fSize_ = 4; epicsType_ = aitEnumInt32; } 
      else { epicsType_ = aitEnumString; }

      log_->info("Detected Rogue Int with size %i for %s typeStr=%s",
            bitSize, epicsName_.c_str(),typeStr.c_str());
   }

   // Python int
   else if ( typeStr == "int" ) {
      fSize_ = 4; 
      epicsType_ = aitEnumInt32;
      log_->info("Detected python int with size %i for %s typeStr=%s",
            bitSize, epicsName_.c_str(),typeStr.c_str());
   }
 
   // 32-bit Float
   else if ( typeStr == "float" or typeStr == "Float32" ) {
      log_->info("Detected 32-bit float %s: typeStr=%s", epicsName_.c_str(),typeStr.c_str());
      epicsType_ = aitEnumFloat32;
      precision_ = 4;
      fSize_ = 4;
   }

   // 64-bit float
   else if ( typeStr == "Float64" ) {
      log_->info("Detected 64-bit float %s: typeStr=%s", epicsName_.c_str(),typeStr.c_str());
      epicsType_ = aitEnumFloat64;
      precision_ = 4;
      fSize_ = 8;
   }

   // Unknown type maps to string
   if ( epicsType_ == aitEnumInvalid ) {
      log_->info("Detected unknow type for %s typeStr=%s. I wil be map to string.", epicsName_.c_str(),typeStr.c_str());
      epicsType_ = aitEnumString;
   }

   // String are limited to 40 chars, so let's use an array of char instead for strings
   if (epicsType_ == aitEnumString)
   {
      if ( count != 0 ) {
         log_->error("Vector of string not supported in EPICS. Ignoring %\n", epicsName_.c_str());
      } else {
         log_->info("Treating String as waveform of chars for %s typeStr=%s\n", epicsName_.c_str(),typeStr.c_str());
         epicsType_ = aitEnumUint8;
         count      = 300;
         isString_  = true;
      }
   }

   // Vector
   if ( count != 0 ) {
      log_->info("Create vector GDD for %s epicsType_=%i, size=%i",epicsName_.c_str(),epicsType_,count);
      pValue_ = new gddAtomic (gddAppType_value, epicsType_, 1u, count);
      size_   = count;
      max_    = count;
      array_  = true;
   }

   // Scalar
   else {
      log_->info("Create scalar GDD for %s epicsType_=%i",epicsName_.c_str(),epicsType_);
      pValue_ = new gddScalar(gddAppType_value, epicsType_);
   }
}

void rpe::Value::updated() {
   pv_->updated(*pValue_);
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
   pv_ = pv;
}

rpe::Pv * rpe::Value::getPv() {
   return pv_;
}

//---------------------------------------
// EPICS Interface
//---------------------------------------
caStatus rpe::Value::read(gdd &prototype) {
   caStatus ret;
   ret = funcTable_.read(*this, prototype);
   return ret;
}

caStatus rpe::Value::readValue(gdd &value) {
   gddStatus gdds;

   std::lock_guard<std::mutex> lock(mtx_);

   // Make sure access types match
   if ( (array_ && value.isAtomic()) || ((!array_) && value.isScalar()) ) {

      // Call value get within lock
      valueGet();

      gdds = gddApplicationTypeTable::app_table.smartCopy(&value, pValue_);

      if (gdds) return S_cas_noConvert;   
      else return S_casApp_success;
   }
   else return S_cas_noConvert;   
}

caStatus rpe::Value::write(const gdd &value) {
   struct timespec t;
   uint32_t newSize;

   std::lock_guard<std::mutex> lock(mtx_);

   // Array
   if ( array_ && value.isAtomic()) {

      // Bound checking
      if ( value.dimension() != 1 ) return S_casApp_badDimension;
      const gddBounds* pb = value.getBounds ();
      if ( pb[0].first() != 0 ) return S_casApp_outOfBounds;
                      
      // Get size      
      newSize = pb[0].size();
      if ( newSize > max_ ) return S_casApp_outOfBounds;

      pValue_->unreference();
      pValue_ = new gddAtomic (gddAppType_value, epicsType_, 1, newSize);
      pValue_->put(&value);
      size_ = newSize;
   }

   // Scalar
   else if ( (!array_) && value.isScalar() ) {
      pValue_->put(&value);
   }

   // Unsupported type
   else return S_cas_noConvert;   

   // Set the timespec structure to the current time stamp the gdd.
#ifdef __MACH__ // OSX does not have clock_gettime
   clock_serv_t cclock;
   mach_timespec_t mts;
   host_get_clock_service(mach_host_self(), CALENDAR_CLOCK, &cclock);
   clock_get_time(cclock, &mts);
   mach_port_deallocate(mach_task_self(), cclock);
   t.tv_sec = mts.tv_sec;
   t.tv_nsec = mts.tv_nsec;
#else      
   clock_gettime(CLOCK_REALTIME,&t);
#endif
   pValue_->setTimeStamp(&t);

   // Cal value set and update within lock 
   this->valueSet();
   return S_casApp_success;
}

aitEnum rpe::Value::bestExternalType() {
   return pValue_->primitiveType();
}

unsigned rpe::Value::maxDimension() {
   return (array_)?1:0;
}

aitIndex rpe::Value::maxBound(unsigned dimension) {
   if (dimension==0) return max_;
   else return 0;
}

gddAppFuncTableStatus rpe::Value::readStatus(gdd &value) {
   std::lock_guard<std::mutex> lock(mtx_);
   value.putConvert(pValue_->getStat());
   return S_casApp_success;
}

gddAppFuncTableStatus rpe::Value::readSeverity(gdd &value) {
   std::lock_guard<std::mutex> lock(mtx_);
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

   uint32_t nstr;
   uint32_t i;

   if ( epicsType_ == aitEnumEnum16 ) {
      nstr = enums_.size();

      str = new aitFixedString[nstr];

      for (i=0; i < nstr; i++) 
         strncpy(str[i].fixed_string, enums_[i].c_str(), sizeof(str[i].fixed_string));

      value.setDimension(1);
      value.setBound (0,0,nstr);
      value.putRef (str, new rpe::Destructor<aitFixedString *>);
 
      return S_cas_success;
   }

   return S_cas_success;
}

