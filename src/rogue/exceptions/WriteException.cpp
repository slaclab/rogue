/**
 *-----------------------------------------------------------------------------
 * Title      : Write Exception
 * ----------------------------------------------------------------------------
 * File       : WriteException.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Write denied exception for Rogue
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
#include <rogue/exceptions/WriteException.h>
namespace re = rogue::exceptions;
namespace bp = boost::python;

PyObject * re::writeExceptionObj = 0;

re::WriteException::WriteException() {
   sprintf(text_,"Write failed");
}

char const * re::WriteException::what() const throw() {
   return(text_);
}

void re::WriteException::setup_python() {
   bp::class_<re::WriteException>("WriteException",bp::init<>());

   PyObject * typeObj = PyErr_NewException((char *)"rogue.exceptions.WriteException", PyExc_Exception, 0);
   bp::scope().attr("WriteException") = bp::handle<>(bp::borrowed(typeObj));

   re::writeExceptionObj = typeObj;

   bp::register_exception_translator<re::WriteException>(&re::WriteException::translate);
}

void re::WriteException::translate(WriteException const &e) {
   bp::object exc(e); // wrap the C++ exception

   bp::object exc_t(bp::handle<>(bp::borrowed(re::writeExceptionObj)));
   exc_t.attr("cause") = exc; // add the wrapped exception to the Python exception

   PyErr_SetString(re::writeExceptionObj, e.what());
}
