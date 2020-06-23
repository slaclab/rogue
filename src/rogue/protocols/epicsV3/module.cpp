/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue EPICS V3 Interface:
 * ----------------------------------------------------------------------------
 * File       : module.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2018-01-31
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

#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>

#include <rogue/protocols/epicsV3/module.h>
#include <rogue/protocols/epicsV3/Value.h>
#include <rogue/protocols/epicsV3/Variable.h>
#include <rogue/protocols/epicsV3/Command.h>
#include <rogue/protocols/epicsV3/Server.h>
#include <rogue/protocols/epicsV3/Master.h>
#include <rogue/protocols/epicsV3/Slave.h>

namespace bp  = boost::python;
namespace rpe = rogue::protocols::epicsV3;

void rpe::setup_module() {

   // map the IO namespace to a sub-module
   bp::object module(bp::handle<>(bp::borrowed(PyImport_AddModule("rogue.protocols.epicsV3"))));

   // make "from mypackage import class1" work
   bp::scope().attr("epicsV3") = module;

   // set the current scope to the new sub-module
   bp::scope io_scope = module;

   rpe::Value::setup_python();
   rpe::Variable::setup_python();
   rpe::Command::setup_python();
   rpe::Server::setup_python();
   rpe::Master::setup_python();
   rpe::Slave::setup_python();
}

