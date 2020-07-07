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
#include <stdint.h>
#include <thread>
#include <mutex>
#include <vector>
#include <string>

namespace rogue {

   //! Filter
   class LogFilter {
      public:

         std::string name_;
         uint32_t level_;

         LogFilter(std::string name, uint32_t level){
            name_  = name;
            level_ = level;
         }
   };

   //! Logging
   class Logging {

         //! Global Logging level
         static uint32_t gblLevel_;

         //! Logging level lock
         static std::mutex levelMtx_;

         //! List of filters
         static std::vector <rogue::LogFilter *> filters_;

         void intLog ( uint32_t level, const char *format, va_list args);

         //! Local logging level
         uint32_t level_;

         //! Logger name
         std::string name_;

      public:

         static const uint32_t Critical = 50;
         static const uint32_t Error    = 40;
         static const uint32_t Thread   = 35;
         static const uint32_t Warning  = 30;
         static const uint32_t Info     = 20;
         static const uint32_t Debug    = 10;

         static std::shared_ptr<rogue::Logging> create(std::string name, bool quiet=false);

         Logging (std::string name, bool quiet=false);
         ~Logging();

         static void setLevel(uint32_t level);
         static void setFilter(std::string filter, uint32_t level);

         void log(uint32_t level, const char * fmt, ...);
         void critical(const char * fmt, ...);
         void error(const char * fmt, ...);
         void warning(const char * fmt, ...);
         void info(const char * fmt, ...);
         void debug(const char * fmt, ...);

         void logThreadId();

         static void setup_python();
   };

   typedef std::shared_ptr<rogue::Logging> LoggingPtr;
}

#endif

