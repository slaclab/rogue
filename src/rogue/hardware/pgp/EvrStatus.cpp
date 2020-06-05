/**
 *-----------------------------------------------------------------------------
 * Title      : PGP Card EVR Status Class
 * ----------------------------------------------------------------------------
 * File       : EvrStatus.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Wrapper for PgpEvrStatus structure
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
#include <rogue/hardware/pgp/EvrStatus.h>
#include <memory>

namespace rhp = rogue::hardware::pgp;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Create the info class with pointer
rhp::EvrStatusPtr rhp::EvrStatus::create() {
   rhp::EvrStatusPtr r = std::make_shared<rhp::EvrStatus>();
   return(r);
}

void rhp::EvrStatus::setup_python () {
#ifndef NO_PYTHON

   bp::class_<rhp::EvrStatus, rhp::EvrStatusPtr >("EvrStatus",bp::no_init)
      .def_readonly("lane",          &rhp::EvrStatus::lane)
      .def_readonly("linkErrors",    &rhp::EvrStatus::linkErrors)
      .def_readonly("linkUp",        &rhp::EvrStatus::linkUp)
      .def_readonly("runStatus",     &rhp::EvrStatus::runStatus)
      .def_readonly("evrSeconds",    &rhp::EvrStatus::evrSeconds)
      .def_readonly("runCounter",    &rhp::EvrStatus::runCounter)
      .def_readonly("acceptCounter", &rhp::EvrStatus::acceptCounter)
   ;
#endif
}

