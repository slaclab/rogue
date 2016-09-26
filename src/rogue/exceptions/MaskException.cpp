/**
 *-----------------------------------------------------------------------------
 * Title      : Mask Exception
 * ----------------------------------------------------------------------------
 * File       : MaskException.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Mask denied exception for Rogue
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
#include <rogue/exceptions/MaskException.h>
namespace re = rogue::exceptions;
namespace bp = boost::python;

PyObject * re::maskExceptionObj = 0;

re::MaskException::MaskException(uint32_t mask) {
   sprintf(text_,"Set Mask Fail: Mask=0x%x",mask);
}

char const * re::MaskException::what() const throw() {
   return(text_);
}

void re::MaskException::setup_python() {
   bp::class_<re::MaskException>("MaskException",bp::init<uint32_t>());

   PyObject * typeObj = PyErr_NewException((char *)"rogue.exceptions.MaskException", PyExc_Exception, 0);
   bp::scope().attr("MaskException") = bp::handle<>(bp::borrowed(typeObj));

   re::maskExceptionObj = typeObj;

   bp::register_exception_translator<re::MaskException>(&re::MaskException::translate);
}

void re::MaskException::translate(MaskException const &e) {
   bp::object exc(e); // wrap the C++ exception

   bp::object exc_t(bp::handle<>(bp::borrowed(re::maskExceptionObj)));
   exc_t.attr("cause") = exc; // add the wrapped exception to the Python exception

   PyErr_SetString(re::maskExceptionObj, e.what());
}
