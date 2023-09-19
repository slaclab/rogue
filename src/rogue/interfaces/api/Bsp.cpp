/**
 *-----------------------------------------------------------------------------
 * Title      : C++ API Bsp
 * ----------------------------------------------------------------------------
 * File       : Bsp.cpp
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
#include "rogue/interfaces/api/Bsp.h"

#include <boost/make_shared.hpp>
#include <string>

#include "rogue/GeneralError.h"

namespace bp  = boost::python;
namespace ria = rogue::interfaces::api;

// Class factory which returns a pointer to a Bsp (BspPtr)
ria::BspPtr ria::Bsp::create(bp::object obj) {
    ria::BspPtr r = std::make_shared<ria::Bsp>(obj);
    return (r);
}

// Class factory which returns a pointer to a Root (BspPtr)
ria::BspPtr ria::Bsp::create(std::string modName, std::string rootClass) {
    ria::BspPtr r = std::make_shared<ria::Bsp>(modName, rootClass);
    return (r);
}

ria::Bsp::Bsp(boost::python::object obj) {
    this->_obj    = obj;
    this->_name   = std::string(bp::extract<char*>(this->_obj.attr("name")));
    this->_isRoot = false;
}

ria::Bsp::Bsp(std::string modName, std::string rootClass) {
    Py_Initialize();

    bp::object mod = bp::import(modName.c_str());
    this->_obj     = mod.attr(rootClass.c_str())();
    this->_name    = std::string(bp::extract<char*>(this->_obj.attr("name")));
    this->_isRoot  = true;
    this->_obj.attr("start")();

    while (bp::extract<bool>(this->_obj.attr("running")) == false) usleep(10);
}

ria::Bsp::~Bsp() {
    if (this->_isRoot) { this->_obj.attr("stop")(); }
}

void ria::Bsp::addVarListener(void (*func)(std::string, std::string), void (*done)()) {
    if (this->_isRoot)
        this->_obj.attr("_addVarListenerCpp")(func, done);
    else
        throw(rogue::GeneralError::create("Bsp::addVarListener",
                                          "Attempt to execute addVarListener on non Root node %s",
                                          this->_name.c_str()));
}

//! Get Attribute
std::string ria::Bsp::getAttribute(std::string attribute) {
    try {
        return (std::string(bp::extract<char*>(this->_obj.attr(attribute.c_str()))));
    } catch (...) {
        throw(rogue::GeneralError::create("Bsp::getAttribute",
                                          "Invalid attribute %s for node %s",
                                          attribute.c_str(),
                                          this->_name.c_str()));
    }
}

//! Return a sub-node operator
rogue::interfaces::api::Bsp ria::Bsp::operator[](std::string name) {
    try {
        bp::object obj = this->_obj.attr("node")(name);
        return (ria::Bsp(obj));
    } catch (...) {
        throw(rogue::GeneralError::create("Bsp::[]",
                                          "Invalid child node %s for node %s",
                                          name.c_str(),
                                          this->_name.c_str()));
    }
}

//! Return a sub-node
std::shared_ptr<rogue::interfaces::api::Bsp> ria::Bsp::getNode(std::string name) {
    try {
        bp::object obj = this->_obj.attr("getNode")(name);
        return (ria::Bsp::create(obj));
    } catch (...) {
        throw(rogue::GeneralError::create("Bsp::node",
                                          "Invalid child node %s for node %s",
                                          name.c_str(),
                                          this->_name.c_str()));
    }
}

//! Execute command operator
std::string ria::Bsp::operator()(std::string arg) {
    try {
        return (std::string(bp::extract<char*>(this->_obj.attr("callDisp")(arg))));
    } catch (...) { throw(rogue::GeneralError::create("Bsp::()", "Error executing node %s", this->_name.c_str())); }
}

//! Execute command operator without arg
std::string ria::Bsp::operator()() {
    try {
        return (std::string(bp::extract<char*>(this->_obj.attr("callDisp")())));
    } catch (...) { throw(rogue::GeneralError::create("Bsp::()", "Error executing node %s", this->_name.c_str())); }
}

//! Execute command
std::string ria::Bsp::execute(std::string arg) {
    try {
        return (std::string(bp::extract<char*>(this->_obj.attr("callDisp")(arg))));
    } catch (...) {
        throw(rogue::GeneralError::create("Bsp::execute", "Error executing node %s", this->_name.c_str()));
    }
}

//! Execute command without arg
std::string ria::Bsp::execute() {
    try {
        return (std::string(bp::extract<char*>(this->_obj.attr("callDisp")())));
    } catch (...) {
        throw(rogue::GeneralError::create("Bsp::execute", "Error executing node %s", this->_name.c_str()));
    }
}

//! Set value
void ria::Bsp::set(std::string value) {
    try {
        this->_obj.attr("setDisp")(value, false, -1);
    } catch (...) {
        throw(rogue::GeneralError::create("Bsp::set",
                                          "Error setting value %s on node %s",
                                          value.c_str(),
                                          this->_name.c_str()));
    }
}

//! Set value withe write
void ria::Bsp::setWrite(std::string value) {
    try {
        this->_obj.attr("setDisp")(value, true, -1);
    } catch (...) {
        throw(rogue::GeneralError::create("Bsp::set",
                                          "Error setting value %s on node %s",
                                          value.c_str(),
                                          this->_name.c_str()));
    }
}

//! Get value
std::string ria::Bsp::get() {
    try {
        return (std::string(bp::extract<char*>(this->_obj.attr("getDisp")(false, -1))));
    } catch (...) {
        throw(rogue::GeneralError::create("Bsp::set", "Error getting value on node %s", this->_name.c_str()));
    }
}

//! Get value with read
std::string ria::Bsp::readGet() {
    try {
        return (std::string(bp::extract<char*>(this->_obj.attr("getDisp")(true, -1))));
    } catch (...) {
        throw(rogue::GeneralError::create("Bsp::set", "Error getting value on node %s", this->_name.c_str()));
    }
}


boost::python::list ria::Bsp::nodeList() {
    // Retrieve a python list of all nodes in the root tree. 
    return static_cast<boost::python::list>(this->_obj.attr("nodeList"));
}
