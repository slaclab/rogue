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
#include <boost/make_shared.hpp>

namespace rpe = rogue::protocols::epics;
namespace bp  = boost::python;

//! Class creation
rpe::PvAttrPtr rpe::PvAttr::create (std::string roguePath, std::string epicsName, std::string base, uint32_t nelms) {
   rpe::PvAttrPtr r = boost::make_shared<rpe::PvAttr>(roguePath,epicsName,base,nelms);
   return(r);
}

//! Setup class in python
void rpe::PvAttr::setup_python() {

   bp::class_<rpe::PvAttr, rpe::PvAttrPtr, boost::noncopyable >("PvAttr",bp::init<std::string,std::string,std::string,uint32_t>())
      .def("create",         &rpe::PvAttr::create)
      .staticmethod("create")
      .def("roguePath",      &rpe::PvAttr::roguePath)
      .def("epicsName",      &rpe::PvAttr::epicsName)
      .def("units",          &rpe::PvAttr::units)
      .def("setUnits",       &rpe::PvAttr::setUnits)
      .def("precision",      &rpe::PvAttr::precision)
      .def("setPrecision",   &rpe::PvAttr::setPrecision)
   ;
}

//! Class creation
rpe::PvAttr::PvAttr (std::string roguePath, std::string epicsName, std::string base, uint32_t nelms) {
   roguePath_ = roguePath;
   epicsName_ = epicsName;
   base_      = base;
   nelms_     = nelms;

   units_     = "";
   precision_ = 32;

   pValue_ = new gddScalar(gddAppType_value, aitEnumFloat64);
}

std::string rpe::PvAttr::epicsName() {
   return(epicsName_);
}

std::string rpe::PvAttr::roguePath() {
   return(roguePath_);
}

std::string rpe::PvAttr::units() {
   return(units_);
}

void rpe::PvAttr::setUnits(std::string units) {
   units_ = units;
}

uint16_t rpe::PvAttr::precision() {
   return(precision_);
}

void rpe::PvAttr::setPrecision(uint16_t precision) {
   precision_ = precision;
}

gdd * rpe::PvAttr::getVal () {
   return(pValue_);
}

