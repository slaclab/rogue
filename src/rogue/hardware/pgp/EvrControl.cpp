/**
 *-----------------------------------------------------------------------------
 * Title      : PGP Card EVR Control Class
 * ----------------------------------------------------------------------------
 * File       : EvrControl.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Wrapper for PgpEvrControl structure
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
#include <rogue/hardware/pgp/EvrControl.h>
#include <memory>

namespace rhp = rogue::hardware::pgp;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Create the info class with pointer
rhp::EvrControlPtr rhp::EvrControl::create() {
   rhp::EvrControlPtr r = std::make_shared<rhp::EvrControl>();
   return(r);
}

void rhp::EvrControl::setup_python () {
#ifndef NO_PYTHON

   bp::class_<rhp::EvrControl, rhp::EvrControlPtr >("EvrControl",bp::no_init)
      .def_readonly ("lane",        &rhp::EvrControl::lane)
      .def_readwrite("evrEnable",   &rhp::EvrControl::evrEnable)
      .def_readwrite("laneRunMask", &rhp::EvrControl::laneRunMask)
      .def_readwrite("evrSyncEn",   &rhp::EvrControl::evrSyncEn)
      .def_readwrite("evrSyncSel",  &rhp::EvrControl::evrSyncSel)
      .def_readwrite("headerMask",  &rhp::EvrControl::headerMask)
      .def_readwrite("evrSyncWord", &rhp::EvrControl::evrSyncWord)
      .def_readwrite("runCode",     &rhp::EvrControl::runCode)
      .def_readwrite("runDelay",    &rhp::EvrControl::runDelay)
      .def_readwrite("acceptCode",  &rhp::EvrControl::acceptCode)
      .def_readwrite("acceptDelay", &rhp::EvrControl::acceptDelay)
   ;
#endif
}

