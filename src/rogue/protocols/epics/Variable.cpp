/**
 *-----------------------------------------------------------------------------
 * Title      : EPICs PV Attribute Object
 * ----------------------------------------------------------------------------
 * File       : Variable.cpp
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

#ifdef DO_EPICS

#include <boost/python.hpp>
#include <rogue/protocols/epics/Variable.h>
#include <rogue/protocols/epics/Pv.h>
#include <rogue/protocols/epics/Server.h>
#include <rogue/GeneralError.h>
#include <rogue/ScopedGil.h>
#include <rogue/GilRelease.h>
#include <boost/make_shared.hpp>
#include <boost/make_shared.hpp>

namespace rpe = rogue::protocols::epics;
namespace bp  = boost::python;

//! Setup class in python
void rpe::Variable::setup_python() {

   bp::class_<rpe::Variable, rpe::VariablePtr, boost::noncopyable >("Variable",bp::init<std::string, bp::object, bool>())
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
   fromPython(var_.attr("value")());
}

rpe::Variable::~Variable() { }

void rpe::Variable::varUpdated(std::string path, boost::python::object value, std::string disp) {
   if ( inSet_ ) return;

   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(mtx_);
   fromPython(value);
   updated();
}

// Lock held when called
void rpe::Variable::valueGet() {
   if ( syncRead_ ) {
      try {
         fromPython(var_.attr("disp")());
         updated();
      } catch (const std::exception & ex) {
         log_->error("Error getting values from epics: %s\n",epicsName_.c_str());
      }
   }
}

// Lock held when called
void rpe::Variable::fromPython(boost::python::object value) {
   struct timespec t;

   clock_gettime(CLOCK_REALTIME,&t);
   pValue_->setTimeStamp(&t);

   if ( epicsType_ == aitEnumUint8 || epicsType_ == aitEnumUint16 || epicsType_ == aitEnumUint32 ) {
      uint32_t nVal;
      nVal = bp::extract<uint32_t>(value);
      pValue_->putConvert(nVal);
   }

   else if ( epicsType_ == aitEnumInt8 || epicsType_ == aitEnumInt16 || epicsType_ == aitEnumInt32 ) {
      int32_t nVal;
      nVal = bp::extract<int32_t>(value);
      pValue_->putConvert(nVal);
   }

   else if ( epicsType_ == aitEnumFloat32 || epicsType_ == aitEnumFloat64 ) {
      double nVal;
      nVal = bp::extract<double>(value);
      pValue_->putConvert(nVal);
   }

   else if ( epicsType_ == aitEnumString ) {
      aitString nVal;
      nVal = bp::extract<char *>(value);
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

      pValue_->putConvert(idx);
   }

   else throw rogue::GeneralError("Variable::fromPython","Invalid Variable Type");
   this->updated();
}

// Lock already held
void rpe::Variable::valueSet() {
   rogue::ScopedGil gil;

   inSet_ = true;

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

#endif

