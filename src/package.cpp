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

#define PY_ARRAY_UNIQUE_SYMBOL Py_Array_Rogue
#include <numpy/arrayobject.h>
#include <numpy/ndarrayobject.h>
#include <numpy/ndarraytypes.h>

#include <boost/python.hpp>
#include <boost/python/numpy.hpp>
#include <cstdio>

#include "rogue/Version.h"
#include "rogue/module.h"

void * rogue_import_array(void) {
    import_array();
    return NULL;
}


BOOST_PYTHON_MODULE(rogue) {
    rogue_import_array();

    rogue::setup_module();

    printf("Rogue/pyrogue version %s. https://github.com/slaclab/rogue\n", rogue::Version::current().c_str());
};
