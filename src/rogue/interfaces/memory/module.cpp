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

#include <rogue/interfaces/memory/module.h>
#include <rogue/interfaces/memory/Block.h>
#include <rogue/interfaces/memory/Slave.h>
#include <rogue/interfaces/memory/Master.h>
#include <rogue/interfaces/memory/Hub.h>
#include <boost/python.hpp>

namespace bp  = boost::python;
namespace rim = rogue::interfaces::memory;

void rim::setup_module() {

   // map the IO namespace to a sub-module
   bp::object module(bp::handle<>(bp::borrowed(PyImport_AddModule("rogue.interfaces.memory"))));

   // make "from mypackage import class1" work
   bp::scope().attr("memory") = module;

   // set the current scope to the new sub-module
   bp::scope io_scope = module;

   rim::Master::setup_python(); 
   rim::Slave::setup_python(); 
   rim::Block::setup_python(); 
   rim::Hub::setup_python(); 

}

