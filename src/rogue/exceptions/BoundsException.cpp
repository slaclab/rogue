/**
 *-----------------------------------------------------------------------------
 * Title      : Bounds Exception
 * ----------------------------------------------------------------------------
 * File       : BoundsException.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Bounds denied exception for Rogue
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
#include <rogue/exceptions/BoundsException.h>
namespace re = rogue::exceptions;
namespace bp = boost::python;

PyObject * re::boundsExceptionObj = 0;

re::BoundsException::BoundsException (uint32_t req, uint32_t size) {
   sprintf(text_,"Out of bounds. Access %i, Size %i",req,size);
}

char const * re::BoundsException::what() const throw() {
   return(text_);
}

void re::BoundsException::setup_python() {
   bp::class_<re::BoundsException>("BoundsException",bp::init<uint32_t,uint32_t>());

   PyObject * typeObj = PyErr_NewException((char *)"rogue.exceptions.BoundsException", PyExc_Exception, 0);
   bp::scope().attr("BoundsException") = bp::handle<>(bp::borrowed(typeObj));

   re::boundsExceptionObj = typeObj;

   bp::register_exception_translator<re::BoundsException>(&re::BoundsException::translate);
}

void re::BoundsException::translate(BoundsException const &e) {
   bp::object exc(e); // wrap the C++ exception

   bp::object exc_t(bp::handle<>(bp::borrowed(re::boundsExceptionObj)));
   exc_t.attr("cause") = exc; // add the wrapped exception to the Python exception

   PyErr_SetString(re::boundsExceptionObj, e.what());
}
