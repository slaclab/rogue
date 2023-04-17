/**
 *-----------------------------------------------------------------------------
 * Title      : C++ API Command
 * ----------------------------------------------------------------------------
 * File       : Command.h
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
#ifndef __ROGUE_INTERFACE_API_COMMAND_H__
#define __ROGUE_INTERFACE_API_COMMAND_H__
#include <boost/python.hpp>
#include <rogue/interfaces/api/Node.h>
#include <rogue/interfaces/api/Command.h>

namespace rogue {
   namespace interfaces {
      namespace api {

         //! Command Class
         class Command : public rogue::interfaces::api::Variable {

            public:

               //! Create the object
               /**
                * @param obj Python object to map to the command
                */
               Command (boost::python::object obj);
               ~Command();

               //! Class factory which returns a pointer to a Command (CommandPtr)
               /**
                * @param obj Python object to map to the command
                */
               static std::shared_ptr<rogue::interfaces::api::Command> create (boost::python::ojbect obj);

               //! Get return type string
               std::string retTypeStr();

               //! Does command take an arg
               bool arg();

               //! Execute command
               std::string call(std::string arg="");
         };

         typedef boost::shared_ptr<rogue::interfaces::api::Command> CommandPtr;
      }
   }
}

#endif

