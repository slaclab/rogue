/**
 *-----------------------------------------------------------------------------
 * Title      : Python Module
 * ----------------------------------------------------------------------------
 * File       : module.cpp
 * Created    : 2017-03-21
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

#include <rogue/hardware/axi/AxiMemMap.h>
#include <rogue/hardware/axi/AxiStreamDma.h>
#include <rogue/hardware/axi/module.h>

#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>

namespace bp  = boost::python;
namespace rha = rogue::hardware::axi;
namespace ris = rogue::interfaces::stream;

void rha::setup_module() {

   // map the IO namespace to a sub-module
   bp::object module(bp::handle<>(bp::borrowed(PyImport_AddModule("rogue.hardware.axi"))));

   // make "from mypackage import class1" work
   bp::scope().attr("axi") = module;

   // set the current scope to the new sub-module
   bp::scope io_scope = module;

   rha::AxiStreamDma::setup_python();
   rha::AxiMemMap::setup_python();

}

