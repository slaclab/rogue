/**
 *-----------------------------------------------------------------------------
 * Title      : Buffer Exception
 * ----------------------------------------------------------------------------
 * File       : BufferException.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Buffer denied exception for Rogue
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
#include <rogue/exceptions/BufferException.h>
namespace re = rogue::exceptions;
namespace bp = boost::python;

PyObject * re::bufferExceptionObj = 0;

re::BufferException::BufferException() {
   sprintf(text_,"Python Buffer Error");
}

char const * re::BufferException::what() const throw() {
   return(text_);
}

void re::BufferException::setup_python() {
   bp::class_<re::BufferException>("BufferException",bp::init<>());

   PyObject * typeObj = PyErr_NewException((char *)"rogue.exceptions.BufferException", PyExc_Exception, 0);
   bp::scope().attr("BufferException") = bp::handle<>(bp::borrowed(typeObj));

   re::bufferExceptionObj = typeObj;

   bp::register_exception_translator<re::BufferException>(&re::BufferException::translate);
}

void re::BufferException::translate(BufferException const &e) {
   bp::object exc(e); // wrap the C++ exception

   bp::object exc_t(bp::handle<>(bp::borrowed(re::bufferExceptionObj)));
   exc_t.attr("cause") = exc; // add the wrapped exception to the Python exception

   PyErr_SetString(re::bufferExceptionObj, e.what());
}
