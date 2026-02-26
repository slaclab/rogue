/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Common Directives For Rogue
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
#ifndef __ROGUE_DIRECTIVES_H__
#define __ROGUE_DIRECTIVES_H__

/** @brief Use NumPy 1.7+ non-deprecated C-API symbols. */
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
/** @brief Enable Python `Py_ssize_t`-safe API signatures. */
#define PY_SSIZE_T_CLEAN
/** @brief Silence global placeholders warning in newer Boost versions. */
#define BOOST_BIND_GLOBAL_PLACEHOLDERS

/** @brief Enable C++11 mode in bundled CRC++ implementation. */
#define CRCPP_USE_CPP11

#ifndef __STDC_FORMAT_MACROS
    /** @brief Enable PRI* printf format macros from `<inttypes.h>` in C++. */
    #define __STDC_FORMAT_MACROS
#endif

#endif
