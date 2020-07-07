/**
 *-----------------------------------------------------------------------------
 * Title      : Python Module
 * ----------------------------------------------------------------------------
 * File       : module.cpp
 * Created    : 2016-08-08
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

#include <rogue/interfaces/memory/module.h>
#include <rogue/interfaces/memory/Slave.h>
#include <rogue/interfaces/memory/Master.h>
#include <rogue/interfaces/memory/Hub.h>
#include <rogue/interfaces/memory/Constants.h>
#include <rogue/interfaces/memory/Transaction.h>
#include <rogue/interfaces/memory/TransactionLock.h>
#include <rogue/interfaces/memory/TcpClient.h>
#include <rogue/interfaces/memory/TcpServer.h>
#include <rogue/interfaces/memory/Block.h>
#include <rogue/interfaces/memory/Variable.h>

#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>

namespace bp  = boost::python;
namespace rim = rogue::interfaces::memory;

void rim::setup_module() {

   // map the IO namespace to a sub-module
   bp::object module(bp::handle<>(bp::borrowed(PyImport_AddModule("rogue.interfaces.memory"))));

   // make "from mypackage import class1" work
   bp::scope().attr("memory") = module;

   // set the current scope to the new sub-module
   bp::scope io_scope = module;

   // Transaction constants
   bp::scope().attr("Read")   = rim::Read;
   bp::scope().attr("Write")  = rim::Write;
   bp::scope().attr("Post")   = rim::Post;
   bp::scope().attr("Verify") = rim::Verify;

   // Processing constants
   bp::scope().attr("PyFunc") = rim::PyFunc;
   bp::scope().attr("Bytes")  = rim::Bytes;
   bp::scope().attr("UInt")   = rim::UInt;
   bp::scope().attr("Int")    = rim::Int;
   bp::scope().attr("Bool")   = rim::Bool;
   bp::scope().attr("String") = rim::String;
   bp::scope().attr("Float")  = rim::Float;
   bp::scope().attr("Double") = rim::Double;
   bp::scope().attr("Fixed")  = rim::Fixed;
   bp::scope().attr("Custom") = rim::Custom;

   rim::Master::setup_python();
   rim::Slave::setup_python();
   rim::Hub::setup_python();
   rim::Transaction::setup_python();
   rim::TransactionLock::setup_python();
   rim::TcpClient::setup_python();
   rim::TcpServer::setup_python();
   rim::Block::setup_python();
   rim::Variable::setup_python();
}

