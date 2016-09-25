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

re::OpenException::OpenException(char const *path) {
   strcpy(text_,"Open Error: ");
   strncat(text_,path,100-strlen(text_));
}

char const * re::OpenException::what() const throw() {
   return(text_);
}

void re::OpenException::setup_python() {
   //register_exception_translator<my_exception>(&translate);
}

void re::OpenException::translate(OpenException const &e) {
    //PyErr_SetObject(OpenExceptionType, boost::python::object(e).ptr());
    //PyErr_SetString(PyExc_RuntimeError, e.what());
}


