/**
 *-----------------------------------------------------------------------------
 * Title      : Common Rogue Functions
 * ----------------------------------------------------------------------------
 * File       : common.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-08-08
 * Last update: 2016-08-08
 * ----------------------------------------------------------------------------
 * Description:
 * Common rogue functions
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

#include <rogue/common.h>

extern PyThreadState * _PyThreadState_Current;

PyThreadState * PyRogue_SaveThread() {
   PyThreadState * tstate = _PyThreadState_Current;
   if ( tstate && (tstate == PyGILState_GetThisThreadState()) ) return(PyEval_SaveThread());
   else return(NULL);
}

void PyRogue_RestoreThread(PyThreadState * state) {
   if ( state != NULL ) PyEval_RestoreThread(state);
}

