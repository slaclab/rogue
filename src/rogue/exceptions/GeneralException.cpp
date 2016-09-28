/**
 *-----------------------------------------------------------------------------
 * Title      : General Exception
 * ----------------------------------------------------------------------------
 * File       : GeneralException.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * General denied exception for Rogue
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
#include <rogue/exceptions/GeneralException.h>
namespace re = rogue::exceptions;
namespace bp = boost::python;

PyObject * re::generalExceptionObj = 0;

re::GeneralException::GeneralException(std::string text) {
   sprintf(text_,"General Error: %s",text.c_str());
}

char const * re::GeneralException::what() const throw() {
   return(text_);
}

void re::GeneralException::setup_python() {
   bp::class_<re::GeneralException>("GeneralException",bp::init<std::string>());

   PyObject * typeObj = PyErr_NewException((char *)"rogue.exceptions.GeneralException", PyExc_Exception, 0);
   bp::scope().attr("GeneralException") = bp::handle<>(bp::borrowed(typeObj));

   re::generalExceptionObj = typeObj;

   bp::register_exception_translator<re::GeneralException>(&re::GeneralException::translate);
}

void re::GeneralException::translate(GeneralException const &e) {
   bp::object exc(e); // wrap the C++ exception

   bp::object exc_t(bp::handle<>(bp::borrowed(re::generalExceptionObj)));
   exc_t.attr("cause") = exc; // add the wrapped exception to the Python exception

   PyErr_SetString(re::generalExceptionObj, e.what());
}
