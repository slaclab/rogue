/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Exception
 * ----------------------------------------------------------------------------
 * File       : MemoryException.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Memory denied exception for Rogue
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
#include <rogue/exceptions/MemoryException.h>
namespace re = rogue::exceptions;
namespace bp = boost::python;

PyObject * re::memoryExceptionObj = 0;

re::MemoryException::MemoryException(uint32_t error) {
   sprintf(text_,"Memory error detected: 0x%x",error);
}

char const * re::MemoryException::what() const throw() {
   return(text_);
}

void re::MemoryException::setup_python() {
   bp::class_<re::MemoryException>("MemoryException",bp::init<uint32_t>());

   PyObject * typeObj = PyErr_NewException((char *)"rogue.exceptions.MemoryException", PyExc_Exception, 0);
   bp::scope().attr("MemoryException") = bp::handle<>(bp::borrowed(typeObj));

   re::memoryExceptionObj = typeObj;

   bp::register_exception_translator<re::MemoryException>(&re::MemoryException::translate);
}

void re::MemoryException::translate(MemoryException const &e) {
   bp::object exc(e); // wrap the C++ exception

   bp::object exc_t(bp::handle<>(bp::borrowed(re::memoryExceptionObj)));
   exc_t.attr("cause") = exc; // add the wrapped exception to the Python exception

   PyErr_SetString(re::memoryExceptionObj, e.what());
}
