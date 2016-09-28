/**
 *-----------------------------------------------------------------------------
 * Title      : Allocation Exception
 * ----------------------------------------------------------------------------
 * File       : AllocationException.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Allocation denied exception for Rogue
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
#include <rogue/exceptions/AllocationException.h>
namespace re = rogue::exceptions;
namespace bp = boost::python;

PyObject * re::allocationExceptionObj = 0;

re::AllocationException::AllocationException(std::string src, uint32_t size) {
   sprintf(text_,"%s: Failed To Allocate %i Bytes",src.c_str(),size);
}

char const * re::AllocationException::what() const throw() {
   return(text_);
}

void re::AllocationException::setup_python() {
   bp::class_<re::AllocationException>("AllocationException",bp::init<std::string,uint32_t>());

   PyObject * typeObj = PyErr_NewException((char *)"rogue.exceptions.AllocationException", PyExc_Exception, 0);
   bp::scope().attr("AllocationException") = bp::handle<>(bp::borrowed(typeObj));

   re::allocationExceptionObj = typeObj;

   bp::register_exception_translator<re::AllocationException>(&re::AllocationException::translate);
}

void re::AllocationException::translate(AllocationException const &e) {
   bp::object exc(e); // wrap the C++ exception

   bp::object exc_t(bp::handle<>(bp::borrowed(re::allocationExceptionObj)));
   exc_t.attr("cause") = exc; // add the wrapped exception to the Python exception

   PyErr_SetString(re::allocationExceptionObj, e.what());
}
