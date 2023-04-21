/**
 *-----------------------------------------------------------------------------
 * Title      : C++ API Node
 * ----------------------------------------------------------------------------
 * File       : Node.cpp
 * Created    : 2023-04-18
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
#include <boost/make_shared.hpp>
#include <rogue/GeneralError.h>
#include <string>

namespace bp = boost::python;
namespace ria = rogue::interfaces::api;

// Class factory which returns a pointer to a Node (NodePtr)
ria::NodePtr ria::Node::create(bp::object obj) {
   ria::NodePtr r = std::make_shared<ria::Node>(obj);
   return(r);
}

ria::Node::Node () {
   this->_isDevice = false;
   this->_isCommand = false;
   this->_isVariable = false;
}

ria::Node::Node (boost::python::object obj) {
   this->_obj = obj;
   this->_isDevice = false;
   this->_isCommand = false;
   this->_isVariable = false;

   if ( this->_obj.attr("isDevice") ) this->_isDevice = true;
   if ( this->_obj.attr("isCommand") ) this->_isCommand = true;
   if ( this->_obj.attr("isVariable") ) this->_isVariable = true;

   this->_name = std::string(bp::extract<char *>(this->_obj.attr("name")));
}

ria::Node::~Node() { }

////////////////////////////////////////////////////////////
// Standard Node Interface
////////////////////////////////////////////////////////////

//! Get name of node
std::string ria::Node::name() {
   return(std::string(bp::extract<char *>(this->_obj.attr("name"))));
}

//! Get path of node
std::string ria::Node::path() {
   return(std::string(bp::extract<char *>(this->_obj.attr("path"))));
}

//! Get description of node
std::string ria::Node::description() {
   return(std::string(bp::extract<char *>(this->_obj.attr("description"))));
}

//! Get list of sub nodes
std::vector<std::string> ria::Node::nodeList() {
   std::vector<std::string> ret;
   int32_t i;

   bp::list pl = (bp::list)this->_obj.attr("nodeList");

   for (i=0; i < len(pl); i++) ret.push_back(std::string(bp::extract<char *>(pl[i])));

   return ret;
}

//! Return a sub-node operator
rogue::interfaces::api::Node ria::Node::operator [](std::string name) {
   try {
      bp::object obj = this->_obj.attr("node")(name);
      return(ria::Node(obj));
   } catch (...) {
      throw(rogue::GeneralError::create("Node::node", "Invalid child node %s", name));
   }
}

//! Return true if node is a device
bool ria::Node::isDevice() {
   return this->_isDevice;
}

//! Return true if node is a command
bool ria::Node::isCommand() {
   return this->_isCommand;
}

//! Return true if node is a variable
bool ria::Node::isVariable() {
   return this->_isVariable;
}

////////////////////////////////////////////////////////////
// Variable Interface
////////////////////////////////////////////////////////////

//! Get type string
std::string ria::Node::typeStr() {
   if ( this->_isVariable || this->_isCommand ) return(std::string(bp::extract<char *>(this->_obj.attr("typeStr"))));
   else throw(rogue::GeneralError::create("Node::typeStr", "Node %s is not a variable or command", this->_name.c_str()));
}

//! Get precision
int32_t ria::Node::precision() {
   if ( this->_isVariable || this->_isCommand ) return(bp::extract<uint32_t>(this->_obj.attr("typeStr")));
   else throw(rogue::GeneralError::create("Node::precision", "Node %s is not a variable or command", this->_name.c_str()));
}

//! Get enum mapping in yaml format, empty string if no enum
std::string ria::Node::enumYaml() {
   if ( this->_isVariable || this->_isCommand ) return(std::string(bp::extract<char *>(this->_obj.attr("enumYaml"))));
   else throw(rogue::GeneralError::create("Node::enumYaml", "Node %s is not a variable or command", this->_name.c_str()));
}

//! Get mode
std::string ria::Node::mode() {
   if ( this->_isVariable || this->_isCommand ) return(std::string(bp::extract<char *>(this->_obj.attr("mode"))));
   else throw(rogue::GeneralError::create("Node::mode", "Node %s is not a variable or command", this->_name.c_str()));
}

//! Get units
std::string ria::Node::units() {
   if ( this->_isVariable || this->_isCommand ) return(std::string(bp::extract<char *>(this->_obj.attr("units"))));
   else throw(rogue::GeneralError::create("Node::units", "Node %s is not a variable or command", this->_name.c_str()));
}

//! Get minimum
float ria::Node::minimum() {
   if ( this->_isVariable || this->_isCommand ) return(bp::extract<float>(this->_obj.attr("minimum")));
   else throw(rogue::GeneralError::create("Node::minimum", "Node %s is not a variable or command", this->_name.c_str()));
}

//! Get maximum
float ria::Node::maximum() {
   if ( this->_isVariable || this->_isCommand ) return(bp::extract<float>(this->_obj.attr("maximum")));
   else throw(rogue::GeneralError::create("Node::maximum", "Node %s is not a variable or command", this->_name.c_str()));
}

//! Set value
void ria::Node::setDisp(std::string value, bool write, int32_t index) {
   if ( this->_isVariable ) this->_obj.attr("setDisp")(value,write,index);
   else throw(rogue::GeneralError::create("Node::setDisp", "Node %s is not a variable", this->_name.c_str()));
}

//! Get value
std::string ria::Node::getDisp(bool read, int32_t index) {
   if ( this->_isVariable ) return(std::string(bp::extract<char *>(this->_obj.attr("getDisp")(read,index))));
   else throw(rogue::GeneralError::create("Node::getDisp", "Node %s is not a variable", this->_name.c_str()));
}

void ria::Node::addListener(void(*func)(std::string,std::string)) {
   if ( this->_isVariable ) this->_obj.attr("_addListenerCpp")(func);
   else throw(rogue::GeneralError::create("Node::addListenerCpp", "Node %s is not a variable", this->_name.c_str()));
}

////////////////////////////////////////////////////////////
// Command Interface
////////////////////////////////////////////////////////////

//! Get return type string
std::string ria::Node::retTypeStr() {
   if ( this->_isCommand ) return(std::string(bp::extract<char *>(this->_obj.attr("retTypeStr"))));
   else throw(rogue::GeneralError::create("Node::retTypeStr", "Node %s is not a command", this->_name.c_str()));
}

//! Does command take an arg
bool ria::Node::arg() {
   if ( this->_isCommand ) return(bp::extract<bool>(this->_obj.attr("arg")));
   else throw(rogue::GeneralError::create("Node::arg", "Node %s is not a command", this->_name.c_str()));
}

//! Execute command
std::string ria::Node::call(std::string arg) {
   if ( this->_isCommand ) return(std::string(bp::extract<char *>(this->_obj.attr("callDisp")(arg))));
   else throw(rogue::GeneralError::create("Node::call", "Node %s is not a command", this->_name.c_str()));
}

//! Execute command, no arg
std::string ria::Node::call() {
   if ( this->_isCommand ) return(std::string(bp::extract<char *>(this->_obj.attr("callDisp")())));
   else throw(rogue::GeneralError::create("Node::call", "Node %s is not a command", this->_name.c_str()));
}

