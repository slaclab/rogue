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
#include <boost/thread.hpp>

namespace rogue {

   //! Logging
   class Logging {
         //boost::python::object _logging;
         //boost::python::object _logger;
      
         //! Logging level 
         static uint32_t level_; 

         //! Logging level lock
         static boost::mutex levelMtx_;
         
         char * name_;

         void intLog ( uint32_t level, const char *format, va_list args);
         
      public:

         static const uint32_t Critical = 50;
         static const uint32_t Error    = 40;
         static const uint32_t Warning  = 30;
         static const uint32_t Info     = 20;
         static const uint32_t Debug    = 10;

         Logging (const char *name);
         ~Logging();

         static void setLevel(uint32_t level);

         void log(uint32_t level, const char * fmt, ...);
         void critical(const char * fmt, ...);
         void error(const char * fmt, ...);
         void warning(const char * fmt, ...);
         void info(const char * fmt, ...);
         void debug(const char * fmt, ...);

         static void setup_python();
   };

   typedef boost::shared_ptr<rogue::Logging> LoggingPtr;
}

#endif

