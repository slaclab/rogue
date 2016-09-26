/**
 *-----------------------------------------------------------------------------
 * Title      : Bounds Exception
 * ----------------------------------------------------------------------------
 * File       : BoundsException.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Bounds denied exception for Rogue
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
#include <rogue/exceptions/BoundsException.h>
namespace re = rogue::exceptions;

re::BoundsException::BoundsException (uint32_t req, uint32_t size) {
   sprintf(text_,"Out of bounds. Access %i, Size %i",req,size);
}

char const * re::BoundsException::what() const throw() {
   return(text_);
}

void re::BoundsException::setup_python() {
   //register_exception_translator<my_exception>(&translate);
}

void re::BoundsException::translate(BoundsException const &e) {
    //PyErr_SetObject(BoundsExceptionType, boost::python::object(e).ptr());
    //PyErr_SetString(PyExc_RuntimeError, e.what());
}

