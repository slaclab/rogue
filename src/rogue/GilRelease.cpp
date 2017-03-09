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
#include <boost/python.hpp>
#include <stdint.h>
#include <rogue/GilRelease.h>

extern PyThreadState * _PyThreadState_Current;

rogue::GilRelease::GilRelease() {
   state_ = NULL;
   release();
}

rogue::GilRelease::~GilRelease() {
   acquire();
}

void rogue::GilRelease::acquire() {
   if ( state_ != NULL ) PyEval_RestoreThread(state_);
   state_ = NULL;
}

void rogue::GilRelease::release() {
   PyThreadState * tstate = _PyThreadState_Current;
   if ( tstate && (tstate == PyGILState_GetThisThreadState()) ) 
      state_ = PyEval_SaveThread();
   else
      state_ = NULL;
}

void rogue::GilRelease::setup_python() {}

