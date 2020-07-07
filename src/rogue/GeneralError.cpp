/**
 *-----------------------------------------------------------------------------
 * Title      : General Error
 * ----------------------------------------------------------------------------
 * File       : GeneralError.cpp
 * Created    : 2017-12-05
 * ----------------------------------------------------------------------------
 * Description:
 * General exception for Rogue
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
#include <rogue/GeneralError.h>
#include <stdarg.h>

#ifndef NO_PYTHON

#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp = boost::python;

PyObject * rogue::generalErrorObj = 0;

#endif

rogue::GeneralError::GeneralError(std::string src,std::string text) {
   snprintf(text_,BuffSize,"%s: General Error: %s",src.c_str(),text.c_str());
}

rogue::GeneralError rogue::GeneralError::create(std::string src, const char * fmt, ...) {
   char temp[BuffSize];
   va_list args;

   va_start(args,fmt);
   vsnprintf(temp,BuffSize,fmt,args);
   va_end(args);

   return(rogue::GeneralError(src,temp));
}

char const * rogue::GeneralError::what() const throw() {
   return(text_);
}

void rogue::GeneralError::setup_python() {

#ifndef NO_PYTHON

   bp::class_<rogue::GeneralError>("GeneralError",bp::init<std::string,std::string>());

   PyObject * typeObj = PyErr_NewException((char *)"rogue.GeneralError", PyExc_Exception, 0);
   bp::scope().attr("GeneralError") = bp::handle<>(bp::borrowed(typeObj));

   rogue::generalErrorObj = typeObj;

   bp::register_exception_translator<rogue::GeneralError>(&(rogue::GeneralError::translate));

#endif
}

void rogue::GeneralError::translate(GeneralError const &e) {

#ifndef NO_PYTHON

   bp::object exc(e); // wrap the C++ exception

   bp::object exc_t(bp::handle<>(bp::borrowed(rogue::generalErrorObj)));
   exc_t.attr("cause") = exc; // add the wrapped exception to the Python exception

   PyErr_SetString(rogue::generalErrorObj, e.what());
#endif
}

