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

#include <rogue/interfaces/module.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/module.h>
#include <boost/python.hpp>

namespace bp  = boost::python;
namespace ris = rogue::interfaces::stream;

void ris::setup_module() {

   // map the IO namespace to a sub-module
   bp::object module(bp::handle<>(bp::borrowed(PyImport_AddModule("rogue.interfaces.stream"))));

   // make "from mypackage import class1" work
   bp::scope().attr("stream") = module;

   // set the current scope to the new sub-module
   bp::scope io_scope = module;

   bp::class_<ris::Frame, ris::FramePtr, boost::noncopyable>("Frame",bp::no_init)
      .def("getAvailable", &ris::Frame::getAvailable)
      .def("getPayload",   &ris::Frame::getPayload)
      .def("read",         &ris::Frame::readPy)
      .def("write",        &ris::Frame::writePy)
      .def("setError",     &ris::Frame::setError)
      .def("getError",     &ris::Frame::getError)
      .def("setFlags",     &ris::Frame::setFlags)
      .def("getFlags",     &ris::Frame::getFlags)
   ;

   bp::class_<ris::Master, ris::MasterPtr, boost::noncopyable>("Master",bp::init<>())
      .def("create",         &ris::Master::create)
      .staticmethod("create")
      .def("setSlave",       &ris::Master::setSlave)
      .def("addSlave",       &ris::Master::addSlave)
      .def("reqFrame",       &ris::Master::reqFrame)
      .def("sendFrame",      &ris::Master::sendFrame)
   ;

   bp::class_<ris::SlaveWrap, ris::SlaveWrapPtr, boost::noncopyable>("Slave",bp::init<>())
      .def("create",         &ris::Slave::create)
      .staticmethod("create")
      .def("acceptFrame",    &ris::Slave::acceptFrame, &ris::SlaveWrap::defAcceptFrame)
      .def("getAllocCount",  &ris::Slave::getAllocCount)
      .def("getAllocBytes",  &ris::Slave::getAllocBytes)
   ;
}

