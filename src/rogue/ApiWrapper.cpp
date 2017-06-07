/**
 *-----------------------------------------------------------------------------
 * Title      : C++ API Wrapper
 * ----------------------------------------------------------------------------
 * File       : ApiWrapper.cpp
 * Created    : 2017-06-06
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
#include <rogue/ApiWrapper.h>
#include <boost/make_shared.hpp>

namespace bp = boost::python;

rogue::ApiWrapperPtr rogue::ApiWrapper::local(std::string module, std::string rootClass) {
   rogue::ApiWrapperPtr ret = boost::make_shared<rogue::ApiWrapper>(true, module, rootClass);
   return(ret);
}

rogue::ApiWrapperPtr rogue::ApiWrapper::remote(std::string group, std::string root) {
   rogue::ApiWrapperPtr ret = boost::make_shared<rogue::ApiWrapper>(false,group,root);
   return(ret);
}

rogue::ApiWrapper::ApiWrapper (bool local, std::string arg1, std::string arg2) {
   Py_Initialize();

   // Load script
   if ( local ) {
      bp::object mod = bp::import(arg1.c_str());
      _root = mod.attr(arg2.c_str())();
   } 
  
   // Remote objects 
   else {
      bp::object pr = bp::import("pyrogue");

      _client = pr.attr("PyroClient")(arg1);
      _root   = _client.attr("getRoot")(arg2);
   }
}

rogue::ApiWrapper::~ApiWrapper() { }

void rogue::ApiWrapper::exec(std::string path, std::string arg) {
   _root.attr("exec")(path)(arg);
}

void rogue::ApiWrapper::exec(std::string path, uint64_t arg) {
   _root.attr("exec")(path)(arg);
}

uint64_t rogue::ApiWrapper::get(std::string path) {
   uint64_t ret = bp::extract<uint64_t>(_root.attr("get")(path));
   return(ret);
}

std::string rogue::ApiWrapper::getDisp(std::string path) {
   char * ret = bp::extract<char *>(_root.attr("getDisp")(path));
   return(std::string(ret));
}

uint64_t rogue::ApiWrapper::value(std::string path) {
   uint64_t ret = bp::extract<uint64_t>(_root.attr("value")(path));
   return(ret);
}

std::string rogue::ApiWrapper::valueDisp(std::string path) {
   char * ret = bp::extract<char *>(_root.attr("valueDisp")(path));
   return(std::string(ret));
}

void rogue::ApiWrapper::set(std::string path, uint64_t value) {
   _root.attr("set")(path)(value);
}

void rogue::ApiWrapper::setDisp(std::string path, std::string value) {
   _root.attr("set")(path)(value);
}

