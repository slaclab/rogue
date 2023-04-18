/**
 *-----------------------------------------------------------------------------
 * Title      : C++ API Root
 * ----------------------------------------------------------------------------
 * File       : Root.cpp
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
#include <rogue/interfaces/api/Root.h>
#include <boost/make_shared.hpp>
#include <rogue/GeneralError.h>

namespace bp = boost::python;
namespace ria = rogue::interfaces::api;


// Class factory which returns a pointer to a Root (RootPtr)
ria::RootPtr ria::Root::create (std::string modName, std::string rootClass, std::string rootArgs) {
   ria::RootPtr r = std::make_shared<ria::Root>(modName, rootClass,rootArgs);
   return(r);
}

ria::Root::Root (std::string modName, std::string rootClass, std::string rootArgs) {
   Py_Initialize();

   bp::object mod = bp::import(modName.c_str());
   this->_obj = mod.attr(rootClass.c_str())(rootArgs);
}

ria::Root::~Root() {
   this->stop();
}

//! Return a sub-node
std::shared_ptr<rogue::interfaces::api::Node> ria::Root::getNode(const char *name) {
   try {
      bp::object obj = this->_obj.attr("getNode")(name);
      return(ria::Node::create(obj));
   } catch (...) {
      throw(rogue::GeneralError::create("Node::node", "Invalid child node %s", name));
   }
}


//! Start root
void ria::Root::start() {
   this->_obj.attr("start")();
}

//! Stop root
void ria::Root::stop() {
   this->_obj.attr("stop")();
}

//! Root is running
bool ria::Root::running() {
   return (bp::extract<bool>(this->_obj.attr("running")));
}

