/**
 *-----------------------------------------------------------------------------
 * Title      : Python Module For Stream Interface
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

#include <rogue/exceptions/module.h>
#include <rogue/exceptions/AllocException.h>
#include <rogue/exceptions/MaskException.h>
#include <rogue/exceptions/OpenException.h>
#include <rogue/exceptions/TimeoutException.h>
#include <rogue/exceptions/WriteException.h>
#include <rogue/exceptions/MemoryException.h>
#include <boost/python.hpp>

namespace bp  = boost::python;
namespace re  = rogue::exceptions;

void re::setup_module() {

   // map the IO namespace to a sub-module
   bp::object module(bp::handle<>(bp::borrowed(PyImport_AddModule("rogue.exceptions"))));

   // make "from mypackage import class1" work
   bp::scope().attr("exceptions") = module;

   // set the current scope to the new sub-module
   bp::scope io_scope = module;

   re::AllocException::setup_python();
   re::MaskException::setup_python();
   re::OpenException::setup_python();
   re::TimeoutException::setup_python();
   re::WriteException::setup_python();
   re::MemoryException::setup_python();
}

