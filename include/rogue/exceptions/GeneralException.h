/**
 *-----------------------------------------------------------------------------
 * Title      : General Exception
 * ----------------------------------------------------------------------------
 * File       : GeneralException.h
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
#ifndef __ROGUE_EXCEPTIONS_WRITE_EXCEPTION_H__
#define __ROGUE_EXCEPTIONS_WRITE_EXCEPTION_H__
#include <exception>
#include <boost/python.hpp>
#include <stdint.h>

namespace rogue {
   namespace exceptions {

      extern PyObject * generalExceptionObj;

      //! General exception
      /*
       * Called for all general errors that should not occur
       * in the system.
       */
      class GeneralException : public std::exception {
            char text_[100];
         public:
            GeneralException (std::string text);
            char const * what() const throw();
            static void setup_python();
            static void translate(GeneralException const &e);
      };
   }
}

#endif

