/**
 *-----------------------------------------------------------------------------
 * Title      : PGP Card Info Class
 * ----------------------------------------------------------------------------
 * File       : Info.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Wrapper for PgpInfo structure
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

#include <rogue/hardware/pgp/Info.h>
#include <boost/make_shared.hpp>

namespace rhp = rogue::hardware::pgp;
namespace bp  = boost::python;

//! Create the info class with pointer
rhp::InfoPtr rhp::Info::create() {
   rhp::InfoPtr r = boost::make_shared<rhp::Info>();
   return(r);
}

//! Return buildstring in string format
std::string rhp::Info::buildString() {
   return(std::string(buildStamp));
}

void rhp::Info::setup_python() {

   bp::class_<rhp::Info, rhp::InfoPtr>("Info",bp::no_init)
      .def("create",               &rhp::Info::create)
      .staticmethod("create")
      .def_readwrite("serial",     &rhp::Info::serial)
      .def_readwrite("type",       &rhp::Info::type)
      .def_readwrite("version",    &rhp::Info::version)
      .def_readwrite("laneMask",   &rhp::Info::laneMask)
      .def_readwrite("vcPerMask",  &rhp::Info::vcPerMask)
      .def_readwrite("pgpRate",    &rhp::Info::pgpRate)
      .def_readwrite("promPrgEn",  &rhp::Info::promPrgEn)
      .def_readwrite("evrSupport", &rhp::Info::evrSupport)
      .def("buildString",          &rhp::Info::buildString)
   ; 
}

