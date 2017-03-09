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
#include <sys/syscall.h>

namespace bp = boost::python;

// Logging level
uint32_t rogue::Logging::level_ = 0;

// Logging level lock
boost::mutex rogue::Logging::levelMtx_;

rogue::Logging::Logging(const char *name) {

   name_ = (char *)malloc(strlen("pyrogue.") + strlen(name) + 1);
   strcpy(name_,"pyrogue.");
   strcat(name_,name);

   //PyGILState_STATE pyState = PyGILState_Ensure();
   //_logging = bp::import("logging");
   //_logger = _logging.attr("getLogger")(name);
   //PyGILState_Release(pyState);
}

rogue::Logging::~Logging() {
   free(name_);
}

void rogue::Logging::setLevel(uint32_t level) {
   levelMtx_.lock();
   level_ = level;
   levelMtx_.unlock();
}

void rogue::Logging::intLog(uint32_t level, const char * fmt, va_list args) {
   if ( level < level_ ) return;

   printf("%s: ",name_);
   vprintf(fmt,args);
   printf("\n");

   //PyGILState_STATE pyState = PyGILState_Ensure();
   //_logging = bp::import("logging");
   //_logger = _logging.attr("getLogger")(name);
   //_logger.attr(level)(buffer);
   //PyGILState_Release(pyState);
}

void rogue::Logging::log(uint32_t level, const char * fmt, ...) {
   va_list arg;
   va_start(arg,fmt);
   intLog(level,fmt,arg);
   va_end(arg);
}

void rogue::Logging::critical(const char * fmt, ...) {
   va_list arg;
   va_start(arg,fmt);
   intLog(rogue::Logging::Critical,fmt,arg);
   va_end(arg);
}

void rogue::Logging::error(const char * fmt, ...) {
   va_list arg;
   va_start(arg,fmt);
   intLog(rogue::Logging::Error,fmt,arg);
   va_end(arg);
}

void rogue::Logging::warning(const char * fmt, ...) {
   va_list arg;
   va_start(arg,fmt);
   intLog(rogue::Logging::Warning,fmt,arg);
   va_end(arg);
}

void rogue::Logging::info(const char * fmt, ...) {
   va_list arg;
   va_start(arg,fmt);
   intLog(rogue::Logging::Info,fmt,arg);
   va_end(arg);
}

void rogue::Logging::debug(const char * fmt, ...) {
   va_list arg;
   va_start(arg,fmt);
   intLog(rogue::Logging::Debug,fmt,arg);
   va_end(arg);
}

void rogue::Logging::setup_python() {
   bp::class_<rogue::Logging, rogue::LoggingPtr, boost::noncopyable>("Logging",bp::no_init)
      .def("setLevel", &rogue::Logging::setLevel)
      .staticmethod("setLevel")
   ;
}


