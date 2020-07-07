/**
 *-----------------------------------------------------------------------------
 * Title      : PGP Card Status Class
 * ----------------------------------------------------------------------------
 * File       : Status.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Wrapper for PgpStatus structure
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
#include <rogue/hardware/pgp/Status.h>
#include <memory>

namespace rhp = rogue::hardware::pgp;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Create the info class with pointer
rhp::StatusPtr rhp::Status::create() {
   rhp::StatusPtr r = std::make_shared<rhp::Status>();
   return(r);
}

void rhp::Status::setup_python () {
#ifndef NO_PYTHON

   bp::class_<rhp::Status, rhp::StatusPtr>("Status",bp::no_init)
      .def_readonly("lane",          &rhp::Status::lane)
      .def_readonly("loopBack",      &rhp::Status::loopBack)
      .def_readonly("locLinkReady",  &rhp::Status::locLinkReady)
      .def_readonly("remLinkReady",  &rhp::Status::remLinkReady)
      .def_readonly("rxReady",       &rhp::Status::rxReady)
      .def_readonly("txReady",       &rhp::Status::txReady)
      .def_readonly("rxCount",       &rhp::Status::rxCount)
      .def_readonly("cellErrCnt",    &rhp::Status::cellErrCnt)
      .def_readonly("linkDownCnt",   &rhp::Status::linkDownCnt)
      .def_readonly("linkErrCnt",    &rhp::Status::linkErrCnt)
      .def_readonly("fifoErr",       &rhp::Status::fifoErr)
      .def_readonly("remData",       &rhp::Status::remData)
      .def_readonly("remBuffStatus", &rhp::Status::remBuffStatus)
   ;
#endif
}
