/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue EPICS Interface: Command Interface
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

#ifdef DO_EPICS

#include <boost/python.hpp>
#include <rogue/protocols/epics/Command.h>
#include <rogue/protocols/epics/Pv.h>
#include <rogue/protocols/epics/Server.h>
#include <rogue/GeneralError.h>
#include <rogue/ScopedGil.h>
#include <boost/make_shared.hpp>
#include <boost/make_shared.hpp>

namespace rpe = rogue::protocols::epics;
namespace bp  = boost::python;

//! Setup class in python
void rpe::Command::setup_python() {

   bp::class_<rpe::Command, rpe::CommandPtr, boost::noncopyable >("Command",bp::init<std::string, bp::object>());

   bp::implicitly_convertible<rpe::CommandPtr, rpe::VariablePtr>();
}

//! Class creation
rpe::Command::Command (std::string epicsName, bp::object p) : Variable(epicsName,p,false) {
   setAttr_  = "exec";
}

rpe::Command::~Command() { }

#endif
