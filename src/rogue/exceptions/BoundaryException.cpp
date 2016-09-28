/**
 *-----------------------------------------------------------------------------
 * Title      : Boundary Exception
 * ----------------------------------------------------------------------------
 * File       : BoundaryException.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Boundary denied exception for Rogue
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
#include <rogue/exceptions/BoundaryException.h>
namespace re = rogue::exceptions;
namespace bp = boost::python;

PyObject * re::boundaryExceptionObj = 0;

re::BoundaryException::BoundaryException (std::string src, uint32_t req, uint32_t size) {
   sprintf(text_,"%s: Boundary Error. Access %i, Size %i",src.c_str(),req,size);
}

char const * re::BoundaryException::what() const throw() {
   return(text_);
}

void re::BoundaryException::setup_python() {
   bp::class_<re::BoundaryException>("BoundaryException",bp::init<std::string,uint32_t,uint32_t>());

   PyObject * typeObj = PyErr_NewException((char *)"rogue.exceptions.BoundaryException", PyExc_Exception, 0);
   bp::scope().attr("BoundaryException") = bp::handle<>(bp::borrowed(typeObj));

   re::boundaryExceptionObj = typeObj;

   bp::register_exception_translator<re::BoundaryException>(&re::BoundaryException::translate);
}

void re::BoundaryException::translate(BoundaryException const &e) {
   bp::object exc(e); // wrap the C++ exception

   bp::object exc_t(bp::handle<>(bp::borrowed(re::boundaryExceptionObj)));
   exc_t.attr("cause") = exc; // add the wrapped exception to the Python exception

   PyErr_SetString(re::boundaryExceptionObj, e.what());
}
