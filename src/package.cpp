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

#define PY_ARRAY_UNIQUE_SYMBOL Py_Array_Rogue
#include "rogue/Directives.h"

#include <boost/python.hpp>
#include <cstdio>

#include "rogue/Version.h"
#include "rogue/module.h"

#include <numpy/arrayobject.h>

BOOST_PYTHON_MODULE(rogue) {
    // PyEval_InitThreads();

    // Init numpy arrays
    _import_array();

    rogue::setup_module();

    printf("Rogue/pyrogue version %s. https://github.com/slaclab/rogue\n", rogue::Version::current().c_str());
};
