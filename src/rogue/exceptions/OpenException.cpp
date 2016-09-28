/**
 *-----------------------------------------------------------------------------
 * Title      : Open Exception
 * ----------------------------------------------------------------------------
 * File       : OpenException.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Open denied exception for Rogue
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
#include <rogue/exceptions/OpenException.h>
namespace re = rogue::exceptions;
namespace bp = boost::python;

PyObject * re::openExceptionObj = 0;

re::OpenException::OpenException(std::string path, uint32_t mask) {
   if ( mask == 0 )
      sprintf(text_,"Error opening %s",path.c_str());
   else 
      sprintf(text_,"Error opening %s with mask 0x%x",path.c_str(),mask);
}

char const * re::OpenException::what() const throw() {
   return(text_);
}

void re::OpenException::setup_python() {
   bp::class_<re::OpenException>("OpenException",bp::init<std::string,uint32_t>());

   PyObject * typeObj = PyErr_NewException((char *)"rogue.exceptions.OpenException", PyExc_Exception, 0);
   bp::scope().attr("OpenException") = bp::handle<>(bp::borrowed(typeObj));

   re::openExceptionObj = typeObj;

   bp::register_exception_translator<re::OpenException>(&re::OpenException::translate);
}

void re::OpenException::translate(OpenException const &e) {
   bp::object exc(e); // wrap the C++ exception

   bp::object exc_t(bp::handle<>(bp::borrowed(re::openExceptionObj)));
   exc_t.attr("cause") = exc; // add the wrapped exception to the Python exception

   PyErr_SetString(re::openExceptionObj, e.what());
}
