/**
 *-----------------------------------------------------------------------------
 * Title      : Logging interface
 * ----------------------------------------------------------------------------
 * File       : Logging.cpp
 * Created    : 2017-02-28
 * ----------------------------------------------------------------------------
 * Description:
 * Logging interface for pyrogue
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
#include <rogue/Logging.h>
namespace bp = boost::python;

rogue::Logging::Logging(const char *cls) {
   char name[100];
   sprintf(name,"pyrogue.%s",cls);

   PyGILState_STATE pyState = PyGILState_Ensure();
   _logging = bp::import("logging");
   _logger = _logging.attr("getLogger")(name);
   PyGILState_Release(pyState);
}

void rogue::Logging::log(const char *level, const char * fmt, ...) {
   va_list args;
   char buffer[256];

   va_start(args,fmt);
   vsprintf(buffer,fmt,args);
   va_end(args);

   PyGILState_STATE pyState = PyGILState_Ensure();
   _logger.attr(level)(buffer);
   PyGILState_Release(pyState);
}

void rogue::Logging::setup_python() {}

