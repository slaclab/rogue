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

#include <rogue/hardware/rce/module.h>
#include <rogue/hardware/rce/RceStream.h>
#include <rogue/hardware/rce/RceMemory.h>
#include <boost/python.hpp>

namespace bp  = boost::python;
namespace rhr = rogue::hardware::rce;

void rhr::setup_module() {

   // map the IO namespace to a sub-module
   bp::object module(bp::handle<>(bp::borrowed(PyImport_AddModule("rogue.hardware.rce"))));

   // make "from mypackage import class1" work
   bp::scope().attr("rce") = module;

   // set the current scope to the new sub-module
   bp::scope io_scope = module;

   rhr::RceStream::setup_python();
   rhr::RceMemory::setup_python();

}

