/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 *   RoCEv2 Boost.Python sub-module registration - registers rogue.protocols.rocev2.{Core, Server}.
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

#include "rogue/protocols/rocev2/module.h"

#include <boost/python.hpp>

#include "rogue/protocols/rocev2/Core.h"
#include "rogue/protocols/rocev2/Server.h"

namespace bp  = boost::python;
namespace rpr = rogue::protocols::rocev2;

void rpr::setup_module() {
  // Map to rogue.protocols.rocev2 sub-module
  bp::object module(
                    bp::handle<>(bp::borrowed(PyImport_AddModule("rogue.protocols.rocev2"))));

  bp::scope().attr("rocev2") = module;
  bp::scope io_scope = module;

  rpr::Core::setup_python();
  rpr::Server::setup_python();
}
