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

#include <boost/python.hpp>
#include <rogue/protocols/epicsV3/Variable.h>
#include <rogue/protocols/epicsV3/Pv.h>
#include <rogue/protocols/epicsV3/Server.h>
#include <rogue/GeneralError.h>
#include <rogue/ScopedGil.h>
#include <rogue/GilRelease.h>
#include <boost/make_shared.hpp>
#include <boost/make_shared.hpp>

namespace rpe = rogue::protocols::epicsV3;
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

   inSet_    = false;
   var_      = bp::object(p);
   syncRead_ = syncRead;
   setAttr_  = "setDisp";

   // Get type and determe if this is an enum
   type = std::string(bp::extract<char *>(var_.attr("typeStr")));
   isEnum = std::string(bp::extract<char *>(var_.attr("disp"))) == "enum";

   // Init gdd record
   this->initGdd(type, isEnum, 0);

   // Extract units
   boost::python::extract<char *> ret(var_.attr("units"));
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
   if ( epicsType_ == aitEnumString ) fromPython(var_.attr("valueDisp")());
   else fromPython(var_.attr("value")());
}

rpe::Variable::~Variable() { }

void rpe::Variable::varUpdated(std::string path, boost::python::object value, boost::python::object disp) {
   log_->debug("Variable update for %s: Disp=%s", epicsName_.c_str(),(char *)bp::extract<char *>(disp));

   if ( inSet_ ) {
      log_->debug("Ignoring variable update for %s", epicsName_.c_str());
      return;
   }

   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);
   if ( epicsType_ == aitEnumString ) fromPython(disp);
   else fromPython(value);
}

// Lock held when called
void rpe::Variable::valueGet() {
   if ( syncRead_ ) {
      rogue::ScopedGil gil;
      log_->info("Synchronous read for %s",epicsName_.c_str());
      try {
         if ( epicsType_ == aitEnumString ) fromPython(var_.attr("valueDisp")());
         else fromPython(var_.attr("value")());
         updated();
      } catch (const std::exception & ex) {
         log_->error("Error getting values from epics: %s\n",epicsName_.c_str());
      }
   }
}

// Lock held when called
void rpe::Variable::fromPython(boost::python::object value) {
   struct timespec t;
   log_->debug("Python set for %s", epicsName_.c_str());

   clock_gettime(CLOCK_REALTIME,&t);
   pValue_->setTimeStamp(&t);

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

   else if ( epicsType_ == aitEnumString ) {
      aitString nVal;
      nVal = bp::extract<char *>(value);
      log_->info("Python set string for %s: Value=%s", epicsName_.c_str(),(char *)nVal);
      pValue_->putConvert(nVal);
   }

   else if ( epicsType_ == aitEnumEnum16 ) {
      std::string val;
      uint8_t idx;

      boost::python::extract<char *> enumChar(value);
      boost::python::extract<bool>   enumBool(value);

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
   this->updated();
}

// Lock already held
void rpe::Variable::valueSet() {
   rogue::ScopedGil gil;

   inSet_ = true;
   log_->info("Variable set for %s",epicsName_.c_str());

   try {
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

      else if ( epicsType_ == aitEnumString ) {
         aitString nVal;
         pValue_->getConvert(nVal);
         var_.attr(setAttr_.c_str())(nVal);
      }

      else if ( epicsType_ == aitEnumEnum16 ) {
         aitString nVal;
         uint8_t idx;

         pValue_->getConvert(idx);

         if ( idx < enums_.size() ) var_.attr(setAttr_.c_str())(enums_[idx]);
      }
   } catch (const std::exception & ex) {
      log_->error("Error setting value from epics: %s\n",epicsName_.c_str());
   }
   inSet_ = false;
}

