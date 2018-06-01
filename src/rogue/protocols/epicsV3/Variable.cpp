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
#include <boost/make_shared.hpp>
#include <boost/make_shared.hpp>

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
   if ( isString_ ) fromPython(var_.attr("valueDisp")());
   else fromPython(var_.attr("value")());
}

rpe::Variable::~Variable() { }

void rpe::Variable::varUpdated(std::string path, bp::object value, bp::object disp) {
   rogue::GilRelease noGil;

   log_->debug("Variable update for %s: Disp=%s", epicsName_.c_str(),(char *)bp::extract<char *>(disp));
   {
      boost::lock_guard<boost::mutex> lock(mtx_);
      noGil.acquire();

      if (  isString_ ) fromPython(disp);
      else fromPython(value);
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
            if ( isString_ ) fromPython(var_.attr("disp")());
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
            for ( i = 0; i < size_; i++ ) pF[i] = bp::extract<uint8_t>(pl[i]);
         }

         pValue_->putRef(pF, new rpe::Destructor<aitUint8 *>);
      }

      else if ( epicsType_ == aitEnumUint16 ) {
         aitUint16 * pF = new aitUint16[size_];
         for ( i = 0; i < size_; i++ ) pF[i] = bp::extract<uint16_t>(pl[i]);
         pValue_->putRef(pF, new rpe::Destructor<aitUint16 *>);
      }

      else if ( epicsType_ == aitEnumUint32 ) {
         aitUint32 * pF = new aitUint32[size_];
         for ( i = 0; i < size_; i++ ) pF[i] = bp::extract<uint32_t>(pl[i]);
         pValue_->putRef(pF, new rpe::Destructor<aitUint32 *>);
      }

      else if ( epicsType_ == aitEnumInt8 ) {
         aitInt8 * pF = new aitInt8[size_];
         for ( i = 0; i < size_; i++ ) pF[i] = bp::extract<int8_t>(pl[i]);
         pValue_->putRef(pF, new rpe::Destructor<aitInt8 *>);
      }

      else if ( epicsType_ == aitEnumInt16 ) {
         aitInt16 * pF = new aitInt16[size_];
         for ( i = 0; i < size_; i++ ) pF[i] = bp::extract<int16_t>(pl[i]);
         pValue_->putRef(pF, new rpe::Destructor<aitInt16 *>);
      }

      else if ( epicsType_ == aitEnumInt32 ) {
         aitInt32 * pF = new aitInt32[size_];
         for ( i = 0; i < size_; i++ ) pF[i] = bp::extract<int32_t>(pl[i]);
         pValue_->putRef(pF, new rpe::Destructor<aitInt32 *>);
      }

      else if ( epicsType_ == aitEnumFloat32 ) {
         aitFloat32 * pF = new aitFloat32[size_];
         for ( i = 0; i < size_; i++ ) pF[i] = bp::extract<double>(pl[i]);
         pValue_->putRef(pF, new rpe::Destructor<aitFloat32 *>);
      }

      else if ( epicsType_ == aitEnumFloat64 ) {
         aitFloat64 * pF = new aitFloat64[size_];
         for ( i = 0; i < size_; i++ ) pF[i] = bp::extract<double>(pl[i]);
         pValue_->putRef(pF, new rpe::Destructor<aitFloat64 *>);
      }
      else throw rogue::GeneralError("Variable::fromPython","Invalid Variable Type");

   } else {

      if ( epicsType_ == aitEnumUint8 || epicsType_ == aitEnumUint16 || epicsType_ == aitEnumUint32 ) {
         uint32_t nVal;
         nVal = bp::extract<uint32_t>(value);
         log_->info("Python set Uint for %s: Value=%lu", epicsName_.c_str(),nVal);
         pValue_->putConvert(nVal);
      }

      else if ( epicsType_ == aitEnumInt8 || epicsType_ == aitEnumInt16 || epicsType_ == aitEnumInt32 ) {
         int32_t nVal;
         nVal = bp::extract<int32_t>(value);
         log_->info("Python set Int for %s: Value=%li", epicsName_.c_str(),nVal);
         pValue_->putConvert(nVal);
      }

      else if ( epicsType_ == aitEnumFloat32 || epicsType_ == aitEnumFloat64 ) {
         double nVal;
         nVal = bp::extract<double>(value);
         log_->info("Python set double for %s: Value=%f", epicsName_.c_str(),nVal);
         pValue_->putConvert(nVal);
      }

      else if ( epicsType_ == aitEnumEnum16 ) {
         std::string val;
         uint8_t idx;

         bp::extract<char *> enumChar(value);
         bp::extract<bool>   enumBool(value);

         // Enum is a string
         if ( enumChar.check() ) idx = revEnum(std::string(enumChar));

         // Enum is a bool
         else if ( enumBool.check() ) idx = (enumBool)?1:0;

         // Invalid
         else throw rogue::GeneralError("Variable::fromPython","Invalid enum");

         log_->info("Python set enum for %s: Enum Value=%i", epicsName_.c_str(),idx);
         pValue_->putConvert(idx);
      }

      else throw rogue::GeneralError("Variable::fromPython","Invalid Variable Type");
   }

   clock_gettime(CLOCK_REALTIME,&t);
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

