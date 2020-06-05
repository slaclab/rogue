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

#include <RogueConfig.h>

#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>

#include <rogue/protocols/module.h>
#include <rogue/protocols/packetizer/module.h>
#include <rogue/protocols/rssi/module.h>
#include <rogue/protocols/srp/module.h>
#include <rogue/protocols/udp/module.h>
#include <rogue/protocols/batcher/module.h>

#if DO_EPICS_V3
   #include <rogue/protocols/epicsV3/module.h>
#endif

namespace bp  = boost::python;

void rogue::protocols::setup_module() {

   // map the IO namespace to a sub-module
   bp::object module(bp::handle<>(bp::borrowed(PyImport_AddModule("rogue.protocols"))));

   // make "from mypackage import class1" work
   bp::scope().attr("protocols") = module;

   // set the current scope to the new sub-module
   bp::scope io_scope = module;

   rogue::protocols::packetizer::setup_module();
   rogue::protocols::rssi::setup_module();
   rogue::protocols::srp::setup_module();
   rogue::protocols::udp::setup_module();
   rogue::protocols::batcher::setup_module();

#if DO_EPICS_V3
   rogue::protocols::epicsV3::setup_module();
#endif

}

