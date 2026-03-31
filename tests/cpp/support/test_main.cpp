#include "rogue/Directives.h"

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
