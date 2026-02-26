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

/**
 * @brief Generic Rogue exception type.
 *
 * @details
 * Used for runtime errors that are not represented by a more specific
 * exception class. Error messages are formatted as `source: message` and can
 * be propagated to Python via `setup_python()` and `translate()`.
 */
class GeneralError : public std::exception {
    static const uint32_t BuffSize = 600;

    char text_[BuffSize];

  public:
    /**
     * @brief Constructs an error from source and message text.
     * @param src Source/function context string.
     * @param text Error message body.
     */
    GeneralError(std::string src, std::string text);

    /**
     * @brief Creates a formatted error instance.
     * @param src Source/function context string.
     * @param fmt `printf`-style format string for the message body.
     * @return Constructed `GeneralError`.
     */
    static GeneralError create(std::string src, const char* fmt, ...);

    /**
     * @brief Returns exception text for standard exception handling.
     * @return NUL-terminated message string.
     */
    char const* what() const throw();

    /** @brief Registers Python exception translation for `GeneralError`. */
    static void setup_python();

    /**
     * @brief Translates `GeneralError` into a Python exception.
     * @param e Caught exception instance.
     */
    static void translate(GeneralError const& e);
};
}  // namespace rogue

#endif
