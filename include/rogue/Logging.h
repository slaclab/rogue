/**
 *-----------------------------------------------------------------------------
 * Title      : Logging interface
 * ----------------------------------------------------------------------------
 * File       : Logging.h
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
#ifndef __ROGUE_LOGGING_H__
#define __ROGUE_LOGGING_H__
#include <exception>
#include <boost/python.hpp>
#include <stdint.h>

namespace rogue {

   //! Logging
   class Logging {
         boost::python::object _logging;
         boost::python::object _logger;
      public:
         Logging (const char *cls);
         void log(const char *level, const char * fmt, ...);
         static void setup_python();
   };
}

#endif

