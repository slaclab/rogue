/**
 *-----------------------------------------------------------------------------
 * Title      : Align Exception
 * ----------------------------------------------------------------------------
 * File       : AlignException.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Align denied exception for Rogue
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
#include <rogue/exceptions/AlignException.h>
namespace re = rogue::exceptions;
namespace bp = boost::python;

PyObject * re::alignExceptionObj = 0;

re::AlignException::AlignException (uint32_t index, uint32_t size) {
   sprintf(text_,"Alignment error. Index %i, Size %i",index,size);
}

char const * re::AlignException::what() const throw() {
   return(text_);
}

void re::AlignException::setup_python() {
   bp::class_<re::AlignException>("AlignException",bp::init<uint32_t,uint32_t>());

   PyObject * typeObj = PyErr_NewException((char *)"rogue.exceptions.AlignException", PyExc_Exception, 0);
   bp::scope().attr("AlignException") = bp::handle<>(bp::borrowed(typeObj));

   re::alignExceptionObj = typeObj;

   bp::register_exception_translator<re::AlignException>(&re::AlignException::translate);
}

void re::AlignException::translate(AlignException const &e) {
   bp::object exc(e); // wrap the C++ exception

   bp::object exc_t(bp::handle<>(bp::borrowed(re::alignExceptionObj)));
   exc_t.attr("cause") = exc; // add the wrapped exception to the Python exception

   PyErr_SetString(re::alignExceptionObj, e.what());
}
