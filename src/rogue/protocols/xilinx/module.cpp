/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
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

#include "rogue/Directives.h"

#include "rogue/protocols/xilinx/module.h"

#include <boost/python.hpp>

#include "rogue/protocols/xilinx/JtagDriver.h"
#include "rogue/protocols/xilinx/Xvc.h"

namespace bp  = boost::python;
namespace rpx = rogue::protocols::xilinx;

void rpx::setup_module() {
    // map the IO namespace to a sub-module
    bp::object module(bp::handle<>(bp::borrowed(PyImport_AddModule("rogue.protocols.xilinx"))));

    // make "from mypackage import class1" work
    bp::scope().attr("xilinx") = module;

    // set the current scope to the new sub-module
    bp::scope io_scope = module;

    rpx::JtagDriver::setup_python();
    rpx::Xvc::setup_python();
}
