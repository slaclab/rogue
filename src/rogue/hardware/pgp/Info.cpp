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
#include <memory>

namespace rhp = rogue::hardware::pgp;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Create the info class with pointer
rhp::InfoPtr rhp::Info::create() {
   rhp::InfoPtr r = std::make_shared<rhp::Info>();
   return(r);
}

//! Return `build string` in string format
std::string rhp::Info::buildString() {
   return(std::string(buildStamp));
}

void rhp::Info::setup_python() {
#ifndef NO_PYTHON

   bp::class_<rhp::Info, rhp::InfoPtr>("Info",bp::no_init)
      .def_readonly("serial",     &rhp::Info::serial)
      .def_readonly("type",       &rhp::Info::type)
      .def_readonly("version",    &rhp::Info::version)
      .def_readonly("laneMask",   &rhp::Info::laneMask)
      .def_readonly("vcPerMask",  &rhp::Info::vcPerMask)
      .def_readonly("pgpRate",    &rhp::Info::pgpRate)
      .def_readonly("promPrgEn",  &rhp::Info::promPrgEn)
      .def_readonly("evrSupport", &rhp::Info::evrSupport)
      .def("buildString",         &rhp::Info::buildString)
   ;
#endif
}

