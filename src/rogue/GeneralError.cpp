/**
 *-----------------------------------------------------------------------------
 * Title      : General Error
 * ----------------------------------------------------------------------------
 * File       : GeneralError.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-12-05
 * Last update: 2017-12-05
 * ----------------------------------------------------------------------------
 * Description:
 * General exception for Rogue
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
#include <rogue/GeneralError.h>
namespace bp = boost::python;

PyObject * re::generalExceptionObj = 0;

re::GeneralError::GeneralError(std::string src,std::string text) {
   sprintf(text_,"%s: General Error: %s",src.c_str(),text.c_str());
}

GeneralError GeneralError:timeout(std::string src, uint32_t time) {
   char temp[100];

   sprintf("timeout after %i microseconds",time);
   return(GeneralException(src,temp);
}

GeneralError GeneralError:open(std::string src, std::string file) {
   char temp[100];

   sprintf("failed to open file %s",file);
   return(GeneralException(src,temp);
}

GeneralError GeneralError:mask(std::string src, std::string file, std::string mask) {
   char temp[100];

   sprintf("failed to open file %s with mask 0x%x",file,mask);
   return(GeneralException(src,temp);
}

GeneralError GeneralError::boundary(std::string src, uint32_t position, uint32_t limit) {
   char temp[100];

   sprintf("boundary error. Position = %i, Limit = %i",position,limit);
   return(GeneralException(src,temp);
}

GeneralError GeneralError::allocation(std::string src, uint32_t size) {
   char temp[100];

   sprintf("failed to allocate size = %i",size);
   return(GeneralException(src,temp);
}

char const * re::GeneralError::what() const throw() {
   return(text_);
}

void re::GeneralError::setup_python() {
   bp::class_<re::GeneralError>("GeneralError",bp::init<std::string,std::string>());

   PyObject * typeObj = PyErr_NewException((char *)"rogue.exceptions.GeneralError", PyExc_Exception, 0);
   bp::scope().attr("GeneralError") = bp::handle<>(bp::borrowed(typeObj));

   re::generalExceptionObj = typeObj;

   bp::register_exception_translator<re::GeneralError>(&re::GeneralError::translate);
}

void re::GeneralError::translate(GeneralError const &e) {
   bp::object exc(e); // wrap the C++ exception

   bp::object exc_t(bp::handle<>(bp::borrowed(re::generalExceptionObj)));
   exc_t.attr("cause") = exc; // add the wrapped exception to the Python exception

   PyErr_SetString(re::generalExceptionObj, e.what());
}
