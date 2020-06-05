/**
 *-----------------------------------------------------------------------------
 * Title      : Python Module
 * ----------------------------------------------------------------------------
 * File       : module.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-08-08
 * Last update: 2016-08-08
 * ----------------------------------------------------------------------------
 * Description:
 * Python module setup
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

#include <rogue/hardware/pgp/module.h>
#include <rogue/hardware/pgp/PgpCard.h>
#include <rogue/hardware/pgp/Info.h>
#include <rogue/hardware/pgp/Status.h>
#include <rogue/hardware/pgp/PciStatus.h>
#include <rogue/hardware/pgp/EvrStatus.h>
#include <rogue/hardware/pgp/EvrControl.h>
#include <rogue/hardware/pgp/EvrStatus.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/stream/Master.h>

#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>

namespace bp  = boost::python;
namespace rhp = rogue::hardware::pgp;
namespace ris = rogue::interfaces::stream;

void rhp::setup_module() {

   // map the IO namespace to a sub-module
   bp::object module(bp::handle<>(bp::borrowed(PyImport_AddModule("rogue.hardware.pgp"))));

   // make "from mypackage import class1" work
   bp::scope().attr("pgp") = module;

   // set the current scope to the new sub-module
   bp::scope io_scope = module;

   rhp::EvrControl::setup_python();
   rhp::EvrStatus::setup_python();
   rhp::Info::setup_python();
   rhp::Status::setup_python();
   rhp::PciStatus::setup_python();
   rhp::PgpCard::setup_python();

}

