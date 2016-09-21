/**
 *-----------------------------------------------------------------------------
 * Title      : Python Module
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

#include <rogue/interfaces/memory/module.h>
#include <rogue/interfaces/memory/Block.h>
#include <rogue/interfaces/memory/BlockVector.h>
#include <rogue/interfaces/memory/Slave.h>
#include <rogue/interfaces/memory/Master.h>
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

   bp::class_<rim::Block, rim::BlockPtr, boost::noncopyable>("Block",bp::init<uint32_t,uint32_t>())
      .def("create",         &rim::Block::create)
      .staticmethod("create")
      .def("getAddress",     &rim::Block::getAddress)
      .def("getSize",        &rim::Block::getSize)
      .def("getData",        &rim::Block::getDataPy)
      .def("getError",       &rim::Block::getError)
      .def("setError",       &rim::Block::setError)
      .def("getStale",       &rim::Block::getStale)
      .def("setStale",       &rim::Block::setStale)
      .def("getUInt8",       &rim::Block::getUInt8)
      .def("setUInt8",       &rim::Block::setUInt8)
      .def("getUInt32",      &rim::Block::getUInt32)
      .def("setUInt32",      &rim::Block::setUInt32)
      .def("getBits",        &rim::Block::getBits)
      .def("setBits",        &rim::Block::setBits)
   ;

   bp::class_<rim::BlockVector, rim::BlockVectorPtr, boost::noncopyable>("BlockVector",bp::init<>())
      .def("create",         &rim::BlockVector::create)
      .staticmethod("create")
      .def("clear",          &rim::BlockVector::clear)
      .def("append",         &rim::BlockVector::append)
      .def("count",          &rim::BlockVector::count)
      .def("getBlock",       &rim::BlockVector::getBlock)
   ;

   bp::class_<rim::Master, rim::MasterPtr, boost::noncopyable>("Master",bp::init<>())
      .def("create",         &rim::Master::create)
      .staticmethod("create")
      .def("setSlave",       &rim::Master::setSlave)
      .def("reqWrite",       &rim::Master::reqWrite)
      .def("reqWriteSingle", &rim::Master::reqWriteSingle)
      .def("reqRead",        &rim::Master::reqRead)
      .def("reqReadSingle",  &rim::Master::reqReadSingle)
   ;

   bp::class_<rim::SlaveWrap, rim::SlaveWrapPtr, boost::noncopyable>("Slave",bp::init<>())
      .def("create",         &rim::Slave::create)
      .staticmethod("create")
      .def("doWrite",        &rim::Slave::doWrite, &rim::SlaveWrap::defDoWrite)
      .def("doRead",         &rim::Slave::doRead,  &rim::SlaveWrap::defDoRead)
   ;
}

