/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Python package setup
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

#include <boost/python.hpp>

#include "rogue/Version.h"
#include "rogue/module.h"

BOOST_PYTHON_MODULE(rogue) {
    // PyEval_InitThreads();

    rogue::setup_module();

    printf("Rogue/pyrogue version %s. https://github.com/slaclab/rogue\n", rogue::Version::current().c_str());
};
