/**
 *-----------------------------------------------------------------------------
 * Title      : Alloc Exception
 * ----------------------------------------------------------------------------
 * File       : AllocException.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Alloc denied exception for Rogue
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
#include <rogue/exceptions/AllocException.h>
namespace re = rogue::exceptions;

re::AllocException::AllocException(uint32_t size) {
   sprintf(text_,"Failed To Alloc %i Bytes",size);
}

char const * re::AllocException::what() const throw() {
   return(text_);
}

void re::AllocException::setup_python() {
   //register_exception_translator<my_exception>(&translate);
}

void re::AllocException::translate(AllocException const &e) {
    //PyErr_SetObject(AllocExceptionType, boost::python::object(e).ptr());
    //PyErr_SetString(PyExc_RuntimeError, e.what());
}

