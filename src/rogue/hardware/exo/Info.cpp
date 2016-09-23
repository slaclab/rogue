/**
 *-----------------------------------------------------------------------------
 * Title      : Tem Card Info Class
 * ----------------------------------------------------------------------------
 * File       : Info.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Wrapper for TemInfo structure
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

#include <rogue/hardware/exo/Info.h>
#include <boost/make_shared.hpp>
#include <boost/python.hpp>

namespace rhe = rogue::hardware::exo;
namespace bp  = boost::python;

//! Create the info class with pointer
rhe::InfoPtr rhe::Info::create() {
   rhe::InfoPtr r = boost::make_shared<rhe::Info>();
   return(r);
}

//! Return buildstring in string format
std::string rhe::Info::buildString() {
   return(std::string(buildStamp));
}

void rhe::Info::setup_python() {

   bp::class_<rhe::Info, rhe::InfoPtr>("Info",bp::no_init)
      .def("create",               &rhe::Info::create)
      .staticmethod("create")
      .def_readwrite("version",    &rhe::Info::version)
      .def_readwrite("promPrgEn",  &rhe::Info::promPrgEn)
      .def("buildString",          &rhe::Info::buildString)
   ; 
}

