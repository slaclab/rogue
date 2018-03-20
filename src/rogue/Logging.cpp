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
#include <boost/make_shared.hpp>

const uint32_t rogue::Logging::Critical;
const uint32_t rogue::Logging::Error;
const uint32_t rogue::Logging::Warning;
const uint32_t rogue::Logging::Info;
const uint32_t rogue::Logging::Debug;

namespace bp = boost::python;

// Logging level
uint32_t rogue::Logging::gblLevel_ = rogue::Logging::Error;

// Logging level lock
boost::mutex rogue::Logging::levelMtx_;

// Filter list
std::vector <rogue::LogFilter *> rogue::Logging::filters_;

// Crate logger
rogue::LoggingPtr rogue::Logging::create(std::string name) {
   rogue::LoggingPtr log = boost::make_shared<rogue::Logging>(name);
   return log;
}

rogue::Logging::Logging(std::string name) {
   std::vector<rogue::LogFilter *>::iterator it;

   name_ = "pyrogue." + name;

   levelMtx_.lock();

   level_ = gblLevel_;

   for (it=filters_.begin(); it < filters_.end(); it++) {
      if ( name_.find((*it)->name_) == 0 ) {
         if ( (*it)->level_ < level_ ) level_ = (*it)->level_;
      }
   }
   levelMtx_.unlock();

   warning("Starting logger with level = %i",level_);
}

rogue::Logging::~Logging() { }

void rogue::Logging::setLevel(uint32_t level) {
   levelMtx_.lock();
   gblLevel_ = level;
   levelMtx_.unlock();
}

void rogue::Logging::setFilter(std::string name, uint32_t level) {
   levelMtx_.lock();

   rogue::LogFilter *flt = new rogue::LogFilter(name,level);

   filters_.push_back(flt);

   levelMtx_.unlock();
}

void rogue::Logging::intLog(uint32_t level, const char * fmt, va_list args) {
   if ( level < level_ ) return;

   char buffer[1000];
   vsnprintf(buffer,1000,fmt,args);
   printf("%s: %s\n",name_.c_str(),buffer);
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
      .def("setFilter", &rogue::Logging::setFilter)
      .staticmethod("setFilter")
      .def_readonly("Critical", &rogue::Logging::Critical)
      .def_readonly("Error",    &rogue::Logging::Error)
      .def_readonly("Warning",  &rogue::Logging::Warning)
      .def_readonly("Info",     &rogue::Logging::Info)
      .def_readonly("Debug",    &rogue::Logging::Debug)
   ;
}


