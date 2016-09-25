/**
 *-----------------------------------------------------------------------------
 * Title      : Write Exception
 * ----------------------------------------------------------------------------
 * File       : WriteException.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Write denied exception for Rogue
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
#include <rogue/exceptions/WriteException.h>
namespace re = rogue::exceptions;

re::WriteException::WriteException() {
   sprintf(text_,"Write failed");
}

char const * re::WriteException::what() const throw() {
   return(text_);
}

void re::WriteException::setup_python() {
   //register_exception_translator<my_exception>(&translate);
}

void re::WriteException::translate(WriteException const &e) {
    //PyErr_SetObject(WriteExceptionType, boost::python::object(e).ptr());
    //PyErr_SetString(PyExc_RuntimeError, e.what());
}

