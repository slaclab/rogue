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
ria::RootPtr ria::Root::create (std::string modName, std::string rootClass, std::string rootArgs = "") {
   ria::RootPtr r = std::make_shared<ria::Root>(modName, rootClass,rootArgs);
   return(b);
}


ria::Root::Root (std::string modName, std::string rootClass, std::string rootArgs) {

}


ria::Root::Root (boost::python::object obj) {
   _obj = obj;
}

ria::Root::~Root() { }


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
   return (bp::extract<bool>(this->_obj.attr("running"));
}


































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

rogue::ApiEntryList rogue::ApiWrapper::getEntries() {
   rogue::ApiEntryList ret;
   bp::object t;
   int32_t i;

   bp::list pl = (bp::list)_root.attr("variableList");

   for (i=0; i < len(pl); i++) {
      rogue::ApiEntryPtr ptr = boost::make_shared<rogue::ApiEntry>();
      ptr->path    = std::string(bp::extract<char *>(pl[i].attr("path")));
      ptr->typeStr = std::string(bp::extract<char *>(pl[i].attr("typeStr")));
      ptr->hidden  = bp::extract<bool>(pl[i].attr("hidden"));
      ptr->cmd     = bp::extract<bool>(pl[i].attr("isCommand"));

      if ( ptr->cmd ) ptr->cmdArg = bp::extract<bool>(pl[i].attr("arg"));
      else ptr->cmdArg = false;

      ret.push_back(ptr);
   }

   return ret;
}

void rogue::ApiWrapper::execUInt32 (std::string path, uint32_t arg) {
   _root.attr("exec")(path,arg);
}

void rogue::ApiWrapper::execUInt64 (std::string path, uint64_t arg) {
   _root.attr("exec")(path,arg);
}

void rogue::ApiWrapper::execDouble (std::string path, double arg) {
   _root.attr("exec")(path,arg);
}

void rogue::ApiWrapper::execString (std::string path, std::string arg) {
   _root.attr("exec")(path,arg);
}

uint32_t rogue::ApiWrapper::getUInt32 (std::string path) {
   uint32_t ret = bp::extract<uint32_t>(_root.attr("get")(path));
   return(ret);
}

uint64_t rogue::ApiWrapper::getUInt64 (std::string path) {
   uint64_t ret = bp::extract<uint64_t>(_root.attr("get")(path));
   return(ret);
}

double rogue::ApiWrapper::getDouble (std::string path) {
   double ret = bp::extract<double>(_root.attr("get")(path));
   return(ret);
}

std::string rogue::ApiWrapper::getString (std::string path) {
   char * ret = bp::extract<char *>(_root.attr("getDisp")(path));
   return(std::string(ret));
}

uint32_t rogue::ApiWrapper::valueUInt32 (std::string path) {
   uint32_t ret = bp::extract<uint32_t> (_root.attr("value")(path));
   return(ret);
}

uint64_t rogue::ApiWrapper::valueUInt64 (std::string path) {
   uint64_t ret = bp::extract<uint64_t>(_root.attr("value")(path));
   return(ret);
}

double rogue::ApiWrapper::valueDouble (std::string path) {
   double ret = bp::extract<double>(_root.attr("value")(path));
   return(ret);
}

std::string rogue::ApiWrapper::valueString (std::string path) {
   char * ret = bp::extract<char *>(_root.attr("valueDisp")(path));
   return(std::string(ret));
}

void rogue::ApiWrapper::setUInt32 (std::string path, uint32_t value) {
   _root.attr("set")(path,value);
}

void rogue::ApiWrapper::setUInt64 (std::string path, uint64_t value) {
   _root.attr("set")(path,value);
}

void rogue::ApiWrapper::setDouble (std::string path, double arg) {
   _root.attr("set")(path,arg);
}

void rogue::ApiWrapper::setString (std::string path, std::string value) {
   _root.attr("set")(path,value);
}

void rogue::ApiWrapper::stop() {
   _root.attr("stop")();
}

std::string rogue::ApiWrapper::getYaml() {
   char * ret = bp::extract<char *>(_root.attr("getYaml")());
   return(std::string(ret));
}

void rogue::ApiWrapper::setYaml(std::string yml) {
   _root.attr("setYaml")(yml);
}

std::string rogue::ApiWrapper::getLog() {
   char * ret = bp::extract<char *>(_root.attr("get")("systemLog"));
   return(std::string(ret));
}

void rogue::ApiWrapper::clrLog() {
   _root.attr("clearLog")();
}

