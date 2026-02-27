/**
 * @brief Central NumPy C-API include point for Rogue.
 *
 * @details
 * This header performs the one-time NumPy C-API symbol import for Rogue by
 * defining the unique API symbol and including NumPy core headers.
 *
 * Other translation units that include NumPy headers should define
 * `NO_IMPORT_ARRAY` before including NumPy C-API headers to avoid duplicate
 * import definitions.
 */

#ifndef __ROGUE_NUMPY_H__
#define __ROGUE_NUMPY_H__

#define NPY_API_SYMBOL_ATTRIBUTE
#define PY_ARRAY_UNIQUE_SYMBOL Py_Array_Rogue
#include <numpy/arrayobject.h>
#include <numpy/ndarraytypes.h>

#endif
