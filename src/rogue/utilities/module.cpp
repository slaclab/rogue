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

#include "rogue/utilities/module.h"

#include <boost/python.hpp>

#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/utilities/Prbs.h"
#include "rogue/utilities/StreamUnZip.h"
#include "rogue/utilities/StreamZip.h"
#include "rogue/utilities/fileio/module.h"

namespace bp  = boost::python;
namespace ru  = rogue::utilities;
namespace ris = rogue::interfaces::stream;

void ru::setup_module() {
    // map the IO namespace to a sub-module
    bp::object module(bp::handle<>(bp::borrowed(PyImport_AddModule("rogue.utilities"))));

    // make "from mypackage import class1" work
    bp::scope().attr("utilities") = module;

    // set the current scope to the new sub-module
    bp::scope io_scope = module;

    ru::Prbs::setup_python();
    ru::StreamZip::setup_python();
    ru::StreamUnZip::setup_python();
    ru::fileio::setup_module();
}
