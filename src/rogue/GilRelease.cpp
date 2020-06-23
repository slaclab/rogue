/**
 *-----------------------------------------------------------------------------
 * Title      : Release GIL within scope.
 * ----------------------------------------------------------------------------
 * File       : GilRelease.cpp
 * Created    : 2017-02-28
 * ----------------------------------------------------------------------------
 * Description:
 * Release GIL for the scope of this class.
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
#include <stdint.h>
#include <rogue/GilRelease.h>

#ifndef NO_PYTHON

#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp = boost::python;
#endif

rogue::GilRelease::GilRelease() {
#ifndef NO_PYTHON
   state_ = NULL;
   release();
#endif
}

rogue::GilRelease::~GilRelease() {
#ifndef NO_PYTHON
   acquire();
#endif
}

void rogue::GilRelease::acquire() {
#ifndef NO_PYTHON
   if ( state_ != NULL ) PyEval_RestoreThread(state_);
   state_ = NULL;
#endif
}

void rogue::GilRelease::release() {
#ifndef NO_PYTHON
   if ( Py_IsInitialized() && PyGILState_Check() )
      state_ = PyEval_SaveThread();
   else state_ = NULL;
#endif
}

