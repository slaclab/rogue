/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
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
#ifndef __ROGUE_GENERAL_ERROR_H__
#define __ROGUE_GENERAL_ERROR_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <exception>
#include <memory>
#include <string>

#ifndef NO_PYTHON
    #include <boost/python.hpp>
#endif

namespace rogue {

#ifndef NO_PYTHON
extern PyObject* generalErrorObj;
#endif

//! General exception
/*
 * Called for all general errors that should not occur
 * in the system.
 */
class GeneralError : public std::exception {
    static const uint32_t BuffSize = 600;

    char text_[BuffSize];

  public:
    GeneralError(std::string src, std::string text);

    static GeneralError create(std::string src, const char* fmt, ...);

    char const* what() const throw();
    static void setup_python();
    static void translate(GeneralError const& e);
};
}  // namespace rogue

#endif
