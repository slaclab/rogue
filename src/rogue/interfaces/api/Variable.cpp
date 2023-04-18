/**
 *-----------------------------------------------------------------------------
 * Title      : C++ API Variable
 * ----------------------------------------------------------------------------
 * File       : Variable.cpp
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
#include <rogue/interfaces/api/Variable.h>
#include <boost/make_shared.hpp>
#include <rogue/GeneralError.h>

namespace bp = boost::python;
namespace ria = rogue::interfaces::api;


// Class factory which returns a pointer to a Variable (VariablePtr)
ria::VariablePtr ria::Variable::create (bp::object obj) {
   ria::VariablePtr r = std::make_shared<ria::Variable>(obj);
   return(b);
}

ria::Variable::Variable (boost::python::object obj) {
   _obj = obj;
}

ria::Variable::~Variable() { }


//! Get type string
std::string ria::Variable::typeStr() {
   return(std::string(bp::extract<char *>(this->_obj.attr("typeStr"))));
}

//! Get precision
int32_t ria::Variable::precision() {
   return(bp::extract<uint32_t>(this->_obj.attr("typeStr")));
}

//! Get enum mapping in yaml format, empty string if no enum
std::string ria::Variable::enumYaml() {
   return(std::string(bp::extract<char *>(this->_obj.attr("enumYaml"))));
}

//! Get mode
std::string ria::Variable::mode() {
   return(std::string(bp::extract<char *>(this->_obj.attr("mode"))));
}

//! Get units
std::string ria::Variable::units() {
   return(std::string(bp::extract<char *>(this->_obj.attr("units"))));
}

//! Get minimum
float ria::Variable::minimum() {
   return(std::string(bp::extract<float>(this->_obj.attr("minimum"))));
}

//! Get maximum
float ria::Variable::maximum() {
   return(std::string(bp::extract<float>(this->_obj.attr("maximum"))));
}

//! Set value
void ria::Variable::setDisp(std::string value, bool write=true, int32_t index=-1) {

}

//! Get value
std::string ria::Variable::getDisp(bool read=true, int32_t index=-1) {


}

