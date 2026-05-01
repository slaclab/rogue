/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Central NumPy C-API include point for Rogue. This header performs
 * the one-time NumPy C-API symbol import by defining the unique API
 * symbol and including NumPy core headers. Other translation units
 * that include NumPy headers should define NO_IMPORT_ARRAY before
 * including NumPy C-API headers to avoid duplicate import definitions.
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
#ifndef __ROGUE_NUMPY_H__
#define __ROGUE_NUMPY_H__

#define NPY_API_SYMBOL_ATTRIBUTE
#define PY_ARRAY_UNIQUE_SYMBOL Py_Array_Rogue
#include <numpy/arrayobject.h>
#include <numpy/ndarraytypes.h>

#endif
