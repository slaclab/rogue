/**
 *-----------------------------------------------------------------------------
 * Title      : Python Module
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

#include <boost/python.hpp>
#include <rogue/protocols/epics/module.h>
#include <rogue/protocols/epics/Value.h>
#include <rogue/protocols/epics/Variable.h>
#include <rogue/protocols/epics/Command.h>
#include <rogue/protocols/epics/Server.h>
#include <rogue/protocols/epics/Pv.h>
#include <rogue/protocols/epics/Master.h>
#include <rogue/protocols/epics/Slave.h>

namespace bp  = boost::python;
namespace rpe = rogue::protocols::epics;

void rpe::setup_module() {

   // map the IO namespace to a sub-module
   bp::object module(bp::handle<>(bp::borrowed(PyImport_AddModule("rogue.protocols.epics"))));

   // make "from mypackage import class1" work
   bp::scope().attr("epics") = module;

   // set the current scope to the new sub-module
   bp::scope io_scope = module;

   rpe::Value::setup_python();
   rpe::Variable::setup_python();
   rpe::Command::setup_python();
   rpe::Server::setup_python();
   rpe::Pv::setup_python();
   rpe::Master::setup_python();
   rpe::Slave::setup_python();
}

