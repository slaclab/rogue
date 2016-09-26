/**
 *-----------------------------------------------------------------------------
 * Title      : Alloc Exception
 * ----------------------------------------------------------------------------
 * File       : AllocException.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Alloc denied exception for Rogue
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
#include <rogue/exceptions/AllocException.h>
namespace re = rogue::exceptions;
namespace bp = boost::python;

PyObject * re::allocExceptionObj = 0;

re::AllocException::AllocException(uint32_t size) {
   sprintf(text_,"Failed To Alloc %i Bytes",size);
}

char const * re::AllocException::what() const throw() {
   return(text_);
}

void re::AllocException::setup_python() {
   bp::class_<re::AllocException>("AllocException",bp::init<uint32_t>());

   PyObject * typeObj = PyErr_NewException((char *)"rogue.exceptions.AllocException", PyExc_Exception, 0);
   bp::scope().attr("AllocException") = bp::handle<>(bp::borrowed(typeObj));

   re::allocExceptionObj = typeObj;

   bp::register_exception_translator<re::AllocException>(&re::AllocException::translate);
}

void re::AllocException::translate(AllocException const &e) {
   bp::object exc(e); // wrap the C++ exception

   bp::object exc_t(bp::handle<>(bp::borrowed(re::allocExceptionObj)));
   exc_t.attr("cause") = exc; // add the wrapped exception to the Python exception

   PyErr_SetString(re::allocExceptionObj, e.what());
}
