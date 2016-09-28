/**
 *-----------------------------------------------------------------------------
 * Title      : Alignment Exception
 * ----------------------------------------------------------------------------
 * File       : AlignmentException.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Alignment denied exception for Rogue
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
#include <rogue/exceptions/AlignmentException.h>
namespace re = rogue::exceptions;
namespace bp = boost::python;

PyObject * re::alignmentExceptionObj = 0;

re::AlignmentException::AlignmentException (uint32_t index, uint32_t size) {
   sprintf(text_,"Alignmentment error. Index %i, Alignment %i",index,size);
}

char const * re::AlignmentException::what() const throw() {
   return(text_);
}

void re::AlignmentException::setup_python() {
   bp::class_<re::AlignmentException>("AlignmentException",bp::init<uint32_t,uint32_t>());

   PyObject * typeObj = PyErr_NewException((char *)"rogue.exceptions.AlignmentException", PyExc_Exception, 0);
   bp::scope().attr("AlignmentException") = bp::handle<>(bp::borrowed(typeObj));

   re::alignmentExceptionObj = typeObj;

   bp::register_exception_translator<re::AlignmentException>(&re::AlignmentException::translate);
}

void re::AlignmentException::translate(AlignmentException const &e) {
   bp::object exc(e); // wrap the C++ exception

   bp::object exc_t(bp::handle<>(bp::borrowed(re::alignmentExceptionObj)));
   exc_t.attr("cause") = exc; // add the wrapped exception to the Python exception

   PyErr_SetString(re::alignmentExceptionObj, e.what());
}
