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
#include <rogue/interfaces/stream/FrameLock.h>
#include <rogue/interfaces/stream/Fifo.h>
#include <rogue/interfaces/stream/Filter.h>
#include <rogue/interfaces/stream/TcpCore.h>
#include <rogue/interfaces/stream/TcpClient.h>
#include <rogue/interfaces/stream/TcpServer.h>
#include <rogue/interfaces/stream/RateDrop.h>
#include <rogue/interfaces/stream/module.h>

#define BOOST_BIND_GLOBAL_PLACEHOLDERS
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

   ris::Frame::setup_python();
   ris::FrameLock::setup_python();
   ris::Master::setup_python();
   ris::Slave::setup_python();
   ris::Pool::setup_python();
   ris::Fifo::setup_python();
   ris::Filter::setup_python();
   ris::TcpCore::setup_python();
   ris::TcpClient::setup_python();
   ris::TcpServer::setup_python();
   ris::RateDrop::setup_python();
}

