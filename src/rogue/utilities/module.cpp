/**
 *-----------------------------------------------------------------------------
 * Title      : Python Module For Stream Interface
 * ----------------------------------------------------------------------------
 * File       : module.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-08-08
 * Last update: 2016-08-08
 * ----------------------------------------------------------------------------
 * Description:
 * Python module setup
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

#include <rogue/utilities/module.h>
#include <rogue/utilities/Prbs.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/stream/Master.h>
#include <boost/python.hpp>

namespace bp  = boost::python;
namespace ru  = rogue::utilities;
namespace ris = rogue::interfaces::stream;

void ru::setup_module() {

   // map the IO namespace to a sub-module
   bp::object module(bp::handle<>(bp::borrowed(PyImport_AddModule("rogue.utilities"))));

   // make "from mypackage import class1" work
   bp::scope().attr("utilities") = module;

   // set the current scope to the new sub-module
   bp::scope io_scope = module;

   bp::class_<ru::Prbs, bp::bases<ris::Master,ris::Slave>, ru::PrbsPtr, boost::noncopyable >("Prbs",bp::init<>())
      .def("create",         &ru::Prbs::create)
      .staticmethod("create")
      .def("genFrame",       &ru::Prbs::genFrame)
      .def("enable",         &ru::Prbs::enable)
      .def("disable",        &ru::Prbs::disable)
      .def("getRxErrors",    &ru::Prbs::getRxErrors)
      .def("getRxCount",     &ru::Prbs::getRxCount)
      .def("getRxBytes",     &ru::Prbs::getRxBytes)
      .def("getTxErrors",    &ru::Prbs::getTxErrors)
      .def("getTxCount",     &ru::Prbs::getTxCount)
      .def("getTxBytes",     &ru::Prbs::getTxBytes)
      .def("resetCount",     &ru::Prbs::resetCount)
      .def("enMessages",     &ru::Prbs::enMessages)
   ;

   bp::implicitly_convertible<ru::PrbsPtr, ris::SlavePtr>();
   bp::implicitly_convertible<ru::PrbsPtr, ris::MasterPtr>();
}

