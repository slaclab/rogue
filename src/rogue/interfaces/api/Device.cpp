/**
 *-----------------------------------------------------------------------------
 * Title      : C++ API Device
 * ----------------------------------------------------------------------------
 * File       : Device.cpp
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
#include <boost/make_shared.hpp>
#include <rogue/GeneralError.h>

namespace bp = boost::python;
namespace ria = rogue::interfaces::api;


// Class factory which returns a pointer to a Device (DevicePtr)
ria::DevicePtr ria::Device::create (bp::object obj) {
   ria::DevicePtr r = std::make_shared<ria::Device>(obj);
   return(r);
}

ria::Device::Device () {}

ria::Device::Device (boost::python::object obj) : ria::Node::Node(obj) {}

ria::Device::~Device() { }


