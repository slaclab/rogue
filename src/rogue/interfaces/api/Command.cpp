/**
 *-----------------------------------------------------------------------------
 * Title      : C++ API Command
 * ----------------------------------------------------------------------------
 * File       : Command.cpp
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
#include <rogue/interfaces/api/Node.h>
#include <rogue/interfaces/api/Command.h>
#include <rogue/interfaces/api/Variable.h>
#include <boost/make_shared.hpp>
#include <rogue/GeneralError.h>

namespace bp = boost::python;
namespace ria = rogue::interfaces::api;


// Class factory which returns a pointer to a Command (CommandPtr)
ria::CommandPtr ria::Command::create (bp::object obj) {
   ria::CommandPtr r = std::make_shared<ria::Command>(obj);
   return(r);
}

ria::Command::Command (boost::python::object obj) : ria::Variable::Variable(obj) {}

ria::Command::~Command() { }


//! Get return type string
std::string ria::Command::retTypeStr() {
   return(std::string(bp::extract<char *>(this->_obj.attr("retTypeStr"))));
}

//! Does command take an arg
bool ria::Command::arg() {
   return(bp::extract<bool>(this->_obj.attr("arg")));
}

//! Execute command
std::string ria::Command::call(std::string arg) {
   return(std::string(bp::extract<char *>(this->_obj.attr("callDisp")(arg))));
}

