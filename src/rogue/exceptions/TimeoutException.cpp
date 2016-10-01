/**
 *-----------------------------------------------------------------------------
 * Title      : Timeout Exception
 * ----------------------------------------------------------------------------
 * File       : TimeoutException.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Timeout denied exception for Rogue
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
#include <rogue/exceptions/TimeoutException.h>

namespace re = rogue::exceptions;
namespace bp = boost::python;

PyObject * re::timeoutExceptionObj = 0;

re::TimeoutException::TimeoutException(std::string src,uint32_t time, uint64_t address) {
   if ( address != 0 ) 
      sprintf(text_,"%s: Timeout after %i microseconds. Address=%lx",src.c_str(),time,address);
   else
      sprintf(text_,"%s: Timeout after %i microseconds",src.c_str(),time);
}

char const * re::TimeoutException::what() const throw() {
   return(text_);
}

void re::TimeoutException::setup_python() {
   bp::class_<re::TimeoutException>("TimeoutException",bp::init<std::string,uint32_t,uint64_t>());

   PyObject * typeObj = PyErr_NewException((char *)"rogue.exceptions.TimeoutException", PyExc_Exception, 0);
   bp::scope().attr("TimeoutException") = bp::handle<>(bp::borrowed(typeObj));

   re::timeoutExceptionObj = typeObj;

   bp::register_exception_translator<re::TimeoutException>(&re::TimeoutException::translate);
}

void re::TimeoutException::translate(TimeoutException const &e) {
   bp::object exc(e); // wrap the C++ exception

   bp::object exc_t(bp::handle<>(bp::borrowed(re::timeoutExceptionObj)));
   exc_t.attr("cause") = exc; // add the wrapped exception to the Python exception

   PyErr_SetString(re::timeoutExceptionObj, e.what());
}

