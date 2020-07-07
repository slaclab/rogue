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

#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>

#include <rogue/module.h>
#include <rogue/interfaces/module.h>
#include <rogue/hardware/module.h>
#include <rogue/utilities/module.h>
#include <rogue/protocols/module.h>
#include <rogue/GeneralError.h>
#include <rogue/Logging.h>
#include <rogue/Version.h>

namespace bp  = boost::python;

void rogue::setup_module() {

   rogue::interfaces::setup_module();
   rogue::protocols::setup_module();
   rogue::hardware::setup_module();
   rogue::utilities::setup_module();

   rogue::GeneralError::setup_python();
   rogue::Logging::setup_python();
   rogue::Version::setup_python();

}

