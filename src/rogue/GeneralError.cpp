/**
 *-----------------------------------------------------------------------------
 * Title      : General Error
 * ----------------------------------------------------------------------------
 * File       : GeneralError.cpp
 * Created    : 2017-12-05
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

PyObject * rogue::generalErrorObj = 0;

rogue::GeneralError::GeneralError(std::string src,std::string text) {
   sprintf(text_,"%s: General Error: %s",src.c_str(),text.c_str());
}

rogue::GeneralError rogue::GeneralError::timeout(std::string src, uint32_t time) {
   char temp[100];

   sprintf(temp,"timeout after %i microseconds",time);
   return(rogue::GeneralError(src,temp));
}

rogue::GeneralError rogue::GeneralError::open(std::string src, std::string file) {
   char temp[100];

   sprintf(temp,"failed to open file %s",file.c_str());
   return(rogue::GeneralError(src,temp));
}

rogue::GeneralError rogue::GeneralError::dest(std::string src, std::string file, uint32_t dest) {
   char temp[100];

   sprintf(temp,"failed to open file %s with dest 0x%x",file.c_str(),dest);
   return(rogue::GeneralError(src,temp));
}

rogue::GeneralError rogue::GeneralError::boundary(std::string src, uint32_t position, uint32_t limit) {
   char temp[100];

   sprintf(temp,"boundary error. Position = %i, Limit = %i",position,limit);
   return(rogue::GeneralError(src,temp));
}

rogue::GeneralError rogue::GeneralError::allocation(std::string src, uint32_t size) {
   char temp[100];

   sprintf(temp,"failed to allocate size = %i",size);
   return(rogue::GeneralError(src,temp));
}

rogue::GeneralError rogue::GeneralError::network(std::string src, std::string host, uint16_t port) {
   char temp[100];

   sprintf(temp,"UDP connect error. Host = %s, Port = %i",host.c_str(),port);
   return(rogue::GeneralError(src,temp));
}

rogue::GeneralError rogue::GeneralError::ret(std::string src, std::string text, int32_t ret) {
   char temp[100];

   sprintf(temp,"%s. Ret=%i",text.c_str(),ret);
   return(rogue::GeneralError(src,temp));
}

char const * rogue::GeneralError::what() const throw() {
   return(text_);
}

void rogue::GeneralError::setup_python() {
   bp::class_<rogue::GeneralError>("GeneralError",bp::init<std::string,std::string>());

   PyObject * typeObj = PyErr_NewException((char *)"rogue.GeneralError", PyExc_Exception, 0);
   bp::scope().attr("GeneralError") = bp::handle<>(bp::borrowed(typeObj));

   rogue::generalErrorObj = typeObj;

   bp::register_exception_translator<rogue::GeneralError>(&(rogue::GeneralError::translate));
}

void rogue::GeneralError::translate(GeneralError const &e) {
   bp::object exc(e); // wrap the C++ exception

   bp::object exc_t(bp::handle<>(bp::borrowed(rogue::generalErrorObj)));
   exc_t.attr("cause") = exc; // add the wrapped exception to the Python exception

   PyErr_SetString(rogue::generalErrorObj, e.what());
}

