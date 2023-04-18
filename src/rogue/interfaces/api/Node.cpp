/**
 *-----------------------------------------------------------------------------
 * Title      : C++ API Node
 * ----------------------------------------------------------------------------
 * File       : Node.cpp
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
#include <rogue/interfaces/api/Device.h>
#include <rogue/interfaces/api/Variable.h>
#include <rogue/interfaces/api/Command.h>
#include <boost/make_shared.hpp>
#include <rogue/GeneralError.h>

namespace bp = boost::python;
namespace ria = rogue::interfaces::api;


// Class factory which returns a pointer to a Node (NodePtr)
ria::NodePtr ria::Node::create (bp::object obj) {
   ria::NodePtr r = std::make_shared<ria::Node>(obj);
   return(b);
}

ria::Node::Node (boost::python::object obj) {
   _obj = obj;
}

ria::Node::~Node() { }

//! Get name of node
std::string ria::Node::name() {
   return(std::string(char * ret = bp::extract<char *>(this->_obj.attr("name"))));
}

//! Get path of node
std::string ria::Node::path() {
   return(std::string(char * ret = bp::extract<char *>(this->_obj.attr("path"))));
}

//! Get description of node
std::string ria::Node::description() {
   return(std::string(char * ret = bp::extract<char *>(this->_obj.attr("description"))));
}

//! Get list of sub nodes
std::vector<std::string> ria::Node::nodeList() {
   std::vector<std::string> ret;
   int32_t i;

   bp::list pl = (bp::list)_root.attr("nodeList");

   for (i=0; i < len(pl); i++) ret.push_back(std::string(bp::extract<char *>(pl[i])));

   return ret;
}

//! Return a sub-node
std::shared_ptr<rogue::interfaces::api::Node> ria::Node::node(std::string name) {
   try {
      bp::object obj = this->_obj.attr(name);

      if ( obj.attr("isDevice") ) return ria::Device::create(obj);
      if ( obj.attr("isCommand") ) return ria::Command::create(obj);
      if ( obj.attr("isVariable") ) return ria::Variable::create(obj);

   } catch() {
      throw(rogue::GeneralError::create("Node::node", "Invalid child node %s", name.c_str()));
   }
}

//! Return a sub-node operator
std::shared_ptr<rogue::interfaces::api::Node> ria::Node::operator [](std::string name) {
   return this->node(name);
}

//! Return true if node is a device
bool ria::Node::isDevice() {
   return bp::extract<bool>(this->_obj.attr("isDevice"));
}

//! Return true if node is a command
bool ria::Node::isCommand() {
   return bp::extract<bool>(this->_obj.attr("isCommand"));
}

//! Return true if node is a variable
bool ria::Node::isVariable() {
   return bp::extract<bool>(this->_obj.attr("isVariable"));
}

