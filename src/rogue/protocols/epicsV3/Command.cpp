/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue EPICS V3 Interface: Command Interface
 * ----------------------------------------------------------------------------
 * File       : Command.cpp
 * Created    : 2018-11-18
 * ----------------------------------------------------------------------------
 * Description:
 * Command subclass of Variable & Value, allows commands to be executed from epics
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

#include <rogue/protocols/epicsV3/Command.h>
#include <rogue/protocols/epicsV3/Pv.h>
#include <rogue/protocols/epicsV3/Server.h>
#include <rogue/GeneralError.h>
#include <memory>

namespace rpe = rogue::protocols::epicsV3;

#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;

//! Setup class in python
void rpe::Command::setup_python() {

   bp::class_<rpe::Command, rpe::CommandPtr, bp::bases<rpe::Variable>, boost::noncopyable >("Command",bp::init<std::string, bp::object>());

   bp::implicitly_convertible<rpe::CommandPtr, rpe::VariablePtr>();
}

//! Class creation
rpe::Command::Command (std::string epicsName, bp::object p) : Variable(epicsName,p,false) {
   setAttr_  = "call";
}

rpe::Command::~Command() { }

