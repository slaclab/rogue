/**
 *-----------------------------------------------------------------------------
 * Title      : C++ API Variable
 * ----------------------------------------------------------------------------
 * File       : Variable.h
 * Created    : 2023-04-17
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
#ifndef __ROGUE_INTERFACE_API_VARIABLE_H__
#define __ROGUE_INTERFACE_API_VARIABLE_H__
#include <boost/python.hpp>
#include <rogue/interfaces/api/Node.h>

namespace rogue {
   namespace interfaces {
      namespace api {

         //! Variable Class
         class Variable : public rogue::interfaces::api::Node {

            public:

               //! Create the object
               /**
                * @param obj Python object to map to the variable
                */
               Variable (boost::python::object obj);
               ~Variable();

               //! Class factory which returns a pointer to a Variable (VariablePtr)
               /**
                * @param obj Python object to map to the variable
                */
               static std::shared_ptr<rogue::interfaces::api::Variable> create (boost::python::ojbect obj);

               //! Get type string
               std::string typeStr();

               //! Get precision
               int8_t precision();

               //! Get enum mapping in yaml format, empty string if no enum
               std::string enum();

               //! Get mode
               std::string mode();

               //! Get units
               std::string units();

               //! Get minimum
               float minimum();

               //! Get maximum
               float maximum();

               //! Set value
               void setDisp(std::string value, bool write=true, int32_t index=-1);

               //! Get value
               std::string getDisp(bool read=true, int32_t index=-1);

         };

         typedef boost::shared_ptr<rogue::interfaces::api::Variable> VariablePtr;
      }
   }
}

#endif

