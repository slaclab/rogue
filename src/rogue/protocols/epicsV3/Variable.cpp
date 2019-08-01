/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue EPICS V3 Interface: Variable Interface
 * ----------------------------------------------------------------------------
 * File       : Variable.cpp
 * Created    : 2018-11-18
 * ----------------------------------------------------------------------------
 * Description:
 * Variable subclass of Value, for interfacing with rogue variables
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

#include <rogue/protocols/epicsV3/Variable.h>
#include <rogue/protocols/epicsV3/Pv.h>
#include <rogue/protocols/epicsV3/Server.h>
#include <rogue/GeneralError.h>
#include <rogue/ScopedGil.h>
#include <rogue/GilRelease.h>
#include <memory>
#include <memory>

#ifdef __MACH__
#include <mach/clock.h>
#include <mach/mach.h>
#endif

namespace rpe = rogue::protocols::epicsV3;

#include <boost/python.hpp>
namespace bp  = boost::python;

//! Setup class in python
void rpe::Variable::setup_python() {

   bp::class_<rpe::Variable, rpe::VariablePtr, bp::bases<rpe::Value>, boost::noncopyable >("Variable",bp::init<std::string, bp::object, bool>())
      .def("varUpdated", &rpe::Variable::varUpdated)
   ;

   bp::implicitly_convertible<rpe::VariablePtr, rpe::ValuePtr>();
}

//! Class creation
rpe::Variable::Variable (std::string epicsName, bp::object p, bool syncRead) : Value(epicsName) {
   std::string type;
   uint32_t    i;
   bool        isEnum;
   bp::dict    ed;
   bp::list    el;
   std::string val;
   char        tmpType[50];
   uint32_t    count;

   var_      = bp::object(p);
   syncRead_ = syncRead;
   setAttr_  = "setDisp";

   // Get type and determe if this is an enum
   type = std::string(bp::extract<char *>(var_.attr("typeStr")));
   isEnum = std::string(bp::extract<char *>(var_.attr("disp"))) == "enum";
   count = 0;

   // Detect list type
   if ( sscanf(type.c_str(),"List[%49[^]]]",&tmpType) == 1 ) {
      type = std::string(tmpType);

      // Get initial element count
      count = len(bp::extract<bp::list>(var_.attr("value")()));
      log_->info("Detected list for %s with type = %s and count = %i", epicsName.c_str(),type.c_str(),count);
   }

   // Init gdd record
   this->initGdd(type, isEnum, count);

   // Extract units
   bp::extract<char *> ret(var_.attr("units"));
   if ( ret.check() && ret != NULL) {
      units_ = std::string(ret);
   }
   else units_ = "";

   //hopr_          = 0;
   //lopr_          = 0;
   //highCtrlLimit_ = 0;
   //lowCtrlLimit_  = 0;

   // Extract enums
   if ( isEnum ) {
      ed = bp::extract<bp::dict>(var_.attr("enum"));
      el = ed.keys();
      enums_.reserve(len(el));

      for (i=0; i < len(el); i++) {
         val = bp::extract<char *>(ed[el[i]]);
         enums_.push_back(val);
      }
   }

   // Init value
   if (  isString_ || epicsType_ == aitEnumEnum16 ) fromPython(var_.attr("valueDisp")());
   else fromPython(var_.attr("value")());
}

rpe::Variable::~Variable() { }

void rpe::Variable::varUpdated(std::string path, bp::object value) {
   rogue::GilRelease noGil;
   bp::object convValue;

   log_->debug("Variable update for %s", epicsName_.c_str());
   {
      std::lock_guard<std::mutex> lock(mtx_);
      noGil.acquire();
  
      if (  isString_ || epicsType_ == aitEnumEnum16 ) convValue = value.attr("valueDisp");
      else convValue = value.attr("value");

      fromPython(convValue);
   }
   noGil.release();
   this->updated();
}

// Lock held when called
void rpe::Variable::valueGet() {
   if ( syncRead_ ) {
      { // GIL Scope
         rogue::ScopedGil gil;
         log_->info("Synchronous read for %s",epicsName_.c_str());
         try {
            if (  isString_ || epicsType_ == aitEnumEnum16 ) fromPython(var_.attr("getDisp")());
            else fromPython(var_.attr("get")());
         } catch (...) {
            log_->error("Error getting values from epics: %s\n",epicsName_.c_str());
         }
      }
   }
}

// Lock held when called
void rpe::Variable::fromPython(bp::object value) {
   struct timespec t;
   bp::list pl;
   std::string ps;
   uint32_t i;

   log_->debug("Python set for %s", epicsName_.c_str());

   if ( array_ ) {

      if ( isString_ ) {
         ps    = bp::extract<std::string>(value);
         size_ = ps.size();
      } else {
         pl    = bp::extract<bp::list>(value);
         size_ = len(pl);
      }

      // Limit size
      if ( size_ > max_ ) size_ = max_;

      // Release old data
      pValue_->unreference();
      pValue_ = new gddAtomic (gddAppType_value, epicsType_, 1u, size_);

      // Create vector of appropriate type
      if ( epicsType_ == aitEnumUint8 ) {
         aitUint8 * pF = new aitUint8[size_];

         if ( isString_ ) {
            ps.copy((char *)pF, size_);
         } else {
            for ( i = 0; i < size_; i++ ) pF[i] = extractValue<uint8_t>(pl[i]);
         }

         pValue_->putRef(pF, new rpe::Destructor<aitUint8 *>);
      }

      else if ( epicsType_ == aitEnumUint16 ) {
         aitUint16 * pF = new aitUint16[size_];
         for ( i = 0; i < size_; i++ ) pF[i] = extractValue<uint16_t>(pl[i]);
         pValue_->putRef(pF, new rpe::Destructor<aitUint16 *>);
      }

      else if ( epicsType_ == aitEnumUint32 ) {
         aitUint32 * pF = new aitUint32[size_];
         for ( i = 0; i < size_; i++ ) pF[i] = extractValue<uint32_t>(pl[i]);
         pValue_->putRef(pF, new rpe::Destructor<aitUint32 *>);
      }

      else if ( epicsType_ == aitEnumInt8 ) {
         aitInt8 * pF = new aitInt8[size_];
         for ( i = 0; i < size_; i++ ) pF[i] = extractValue<int8_t>(pl[i]);
         pValue_->putRef(pF, new rpe::Destructor<aitInt8 *>);
      }

      else if ( epicsType_ == aitEnumInt16 ) {
         aitInt16 * pF = new aitInt16[size_];
         for ( i = 0; i < size_; i++ ) pF[i] = extractValue<int16_t>(pl[i]);
         pValue_->putRef(pF, new rpe::Destructor<aitInt16 *>);
      }

      else if ( epicsType_ == aitEnumInt32 ) {
         aitInt32 * pF = new aitInt32[size_];
         for ( i = 0; i < size_; i++ ) pF[i] = extractValue<int32_t>(pl[i]);
         pValue_->putRef(pF, new rpe::Destructor<aitInt32 *>);
      }

      else if ( epicsType_ == aitEnumFloat32 ) {
         aitFloat32 * pF = new aitFloat32[size_];
         for ( i = 0; i < size_; i++ ) pF[i] = extractValue<double>(pl[i]);
         pValue_->putRef(pF, new rpe::Destructor<aitFloat32 *>);
      }

      else if ( epicsType_ == aitEnumFloat64 ) {
         aitFloat64 * pF = new aitFloat64[size_];
         for ( i = 0; i < size_; i++ ) pF[i] = extractValue<double>(pl[i]);
         pValue_->putRef(pF, new rpe::Destructor<aitFloat64 *>);
      }
      else throw rogue::GeneralError("Variable::fromPython","Invalid Variable Type");

   } else {

      if ( epicsType_ == aitEnumUint8 || epicsType_ == aitEnumUint16 || epicsType_ == aitEnumUint32 ) {
         uint32_t nVal = extractValue<uint32_t>(value);
         log_->info("Python set Uint for %s: Value=%lu", epicsName_.c_str(),nVal);
         pValue_->putConvert(nVal);
      }

      else if ( epicsType_ == aitEnumInt8 || epicsType_ == aitEnumInt16 || epicsType_ == aitEnumInt32 ) {
         int32_t nVal = extractValue<int32_t>(value);
         log_->info("Python set Int for %s: Value=%li", epicsName_.c_str(),nVal);
         pValue_->putConvert(nVal);
      }

      else if ( epicsType_ == aitEnumFloat32 || epicsType_ == aitEnumFloat64 ) {
         double nVal = extractValue<double>(value);
         log_->info("Python set double for %s: Value=%f", epicsName_.c_str(),nVal);
         pValue_->putConvert(nVal);
      }

      else if ( epicsType_ == aitEnumEnum16 ) {
         std::string val;
         uint8_t idx;

         bp::extract<std::string> enumStr(value);
         bp::extract<bool>        enumBool(value);

         // Enum is a string
         if ( enumStr.check() ) idx = revEnum(enumStr);

         // Enum is a bool
         else if ( enumBool.check() ) idx = (enumBool)?1:0;

         // Invalid
         else throw rogue::GeneralError("Variable::fromPython","Invalid enum");

         log_->info("Python set enum for %s: Enum Value=%i", epicsName_.c_str(),idx);
         pValue_->putConvert(idx);
      }

      else throw rogue::GeneralError("Variable::fromPython","Invalid Variable Type");
   }

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
}

// Lock already held
void rpe::Variable::valueSet() {
   rogue::ScopedGil gil;
   bp::list pl;
   uint32_t i;

   log_->info("Variable set for %s",epicsName_.c_str());

   try {
      if ( isString_ ) {

         // Process values that are exposed as string in EPICS
         aitUint8 * pF = new aitUint8[size_];
         pValue_->getRef(pF);
         var_.attr(setAttr_.c_str())(std::string((char*)pF));

      } else if ( array_ ) {

         // Create vector of appropriate type
         if ( epicsType_ == aitEnumUint8 ) {
            aitUint8 * pF = new aitUint8[size_];
            pValue_->getRef(pF);
            for ( i = 0; i < size_; i++ ) pl.append(pF[i]);
         }

         else if ( epicsType_ == aitEnumUint16 ) {
            aitUint16 * pF = new aitUint16[size_];
            pValue_->getRef(pF);
            for ( i = 0; i < size_; i++ ) pl.append(pF[i]);
         }

         else if ( epicsType_ == aitEnumUint32 ) {
            aitUint32 * pF = new aitUint32[size_];
            pValue_->getRef(pF);
            for ( i = 0; i < size_; i++ ) pl.append(pF[i]);
         }

         else if ( epicsType_ == aitEnumInt8 ) {
            aitInt8 * pF = new aitInt8[size_];
            pValue_->getRef(pF);
            for ( i = 0; i < size_; i++ ) pl.append(pF[i]);
         }

         else if ( epicsType_ == aitEnumInt16 ) {
            aitInt16 * pF = new aitInt16[size_];
            pValue_->getRef(pF);
            for ( i = 0; i < size_; i++ ) pl.append(pF[i]);
         }

         else if ( epicsType_ == aitEnumInt32 ) {
            aitInt32 * pF = new aitInt32[size_];
            pValue_->getRef(pF);
            for ( i = 0; i < size_; i++ ) pl.append(pF[i]);
         }

         else if ( epicsType_ == aitEnumFloat32 ) {
            aitFloat32 * pF = new aitFloat32[size_];
            pValue_->getRef(pF);
            for ( i = 0; i < size_; i++ ) pl.append(pF[i]);
         }

         else if ( epicsType_ == aitEnumFloat64 ) {
            aitFloat64 * pF = new aitFloat64[size_];
            pValue_->getRef(pF);
            for ( i = 0; i < size_; i++ ) pl.append(pF[i]);
         }

         var_.attr(setAttr_.c_str())(pl);
      }
      else {

         if ( epicsType_ == aitEnumUint8 || epicsType_ == aitEnumUint16 || epicsType_ == aitEnumUint32 ) {
            uint32_t nVal;
            pValue_->getConvert(nVal);
            var_.attr(setAttr_.c_str())(nVal);
         }

         else if ( epicsType_ == aitEnumInt8 || epicsType_ == aitEnumInt16 || epicsType_ == aitEnumInt32 ) {
            int32_t nVal;
            pValue_->getConvert(nVal);
            var_.attr(setAttr_.c_str())(nVal);
         }

         else if ( epicsType_ == aitEnumFloat32 || epicsType_ == aitEnumFloat64 ) {
            double nVal;
            pValue_->getConvert(nVal);
            var_.attr(setAttr_.c_str())(nVal);
         }

         else if ( epicsType_ == aitEnumEnum16 ) {
            aitString nVal;
            uint8_t idx;

            pValue_->getConvert(idx);
            if ( idx < enums_.size() ) var_.attr(setAttr_.c_str())(enums_[idx]);
         }
      }
   } catch (...) {
      log_->error("Error setting value from epics: %s\n",epicsName_.c_str());
   }
}

template<typename T>
T rpe::Variable::extractValue(boost::python::object value)
{
   bp::extract<T> get_val(value);

   // Check for convertibility
   if (get_val.check())
   {
      // If a conversion is available, return the converted value.
      try
      {
         // An implicit numeric_cast can throw a bad_numeric_cast exception here.
         return get_val();
      }
      catch (boost::numeric::bad_numeric_cast& e)
      {
         // If an exception is thrown, log the error and return zero.
         log_->warning("Variable::extractValue error for %s: %s", epicsName_.c_str(),e.what());
         return 0;
      }
   }
   else
   {
      // If  a conversion is not available, log the error and return zero.
      log_->warning("Variable::extractValue error for %s: boost::python::extract failed", epicsName_.c_str());
      return 0;
   }

}
