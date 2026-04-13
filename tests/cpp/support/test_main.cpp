/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Native C++ test runner entry point for the in-tree Rogue suite, providing
 * the shared doctest runner main and the optional Python/NumPy bootstrap used
 * by Python-enabled smoke tests.
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

#define DOCTEST_CONFIG_IMPLEMENT
#include "doctest/doctest.h"

#ifndef NO_PYTHON

    #include <Python.h>
    #include "rogue/numpy.h"
    #include "support/test_python.h"

#endif

#ifndef NO_PYTHON
int rogue_test_initialize_python_numpy() {
    if (!Py_IsInitialized()) Py_Initialize();
    return _import_array();
}
#endif

int main(int argc, char** argv) {
#ifndef NO_PYTHON
    if (!Py_IsInitialized()) Py_Initialize();
#endif

    doctest::Context context(argc, argv);
    return context.run();
}
