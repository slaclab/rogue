// include the numpy headers once. This will set the PyArray
// pointer globally. Other files that import numpy headers
// must define NO_IMPORT_ARRAY prior
#define NPY_API_SYMBOL_ATTRIBUTE
#define PY_ARRAY_UNIQUE_SYMBOL Py_Array_Rogue
#include <numpy/arrayobject.h>
