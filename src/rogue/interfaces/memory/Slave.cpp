/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Slave
 * ----------------------------------------------------------------------------
 * File       : Slave.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-09-20
 * Last update: 2016-09-20
 * ----------------------------------------------------------------------------
 * Description:
 * Memory slave interface.
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
#include <rogue/interfaces/memory/Slave.h>
#include <rogue/interfaces/memory/Block.h>
#include <boost/make_shared.hpp>

namespace rim = rogue::interfaces::memory;
namespace bp = boost::python;

//! Create a slave container
rim::SlavePtr rim::Slave::create () {
   rim::SlavePtr s = boost::make_shared<rim::Slave>();
   return(s);
}

//! Create object
rim::Slave::Slave() { } 

//! Destroy object
rim::Slave::~Slave() { }

//! Post a transaction
void rim::Slave::doTransaction(bool write, bool posted, rim::BlockPtr block) { }

//! Post a transaction
void rim::SlaveWrap::doTransaction(bool write, bool posted, rim::BlockPtr block) {
   bool found;

   found = false;

   // Not sure if this is (and release) are ok if calling from python to python
   // It appears we need to lock before calling get_override
   PyGILState_STATE pyState = PyGILState_Ensure();

   if (boost::python::override dt = this->get_override("doTransaction")) {
      found = true;
      try {
         dt(write,posted,block);
      } catch (...) {
         PyErr_Print();
      }
   }
   PyGILState_Release(pyState);

   if ( ! found ) rim::Slave::doTransaction(write,posted,block);
}

//! Default doWite call
void rim::SlaveWrap::defTransaction(bool write, bool posted, rim::BlockPtr block) {
   return(rim::Slave::doTransaction(write,posted,block));
}

void rim::Slave::setup_python () {

   bp::class_<rim::SlaveWrap, rim::SlaveWrapPtr, boost::noncopyable>("Slave",bp::init<>())
      .def("create",         &rim::Slave::create)
      .staticmethod("create")
      .def("doTransaction",  &rim::Slave::doTransaction, &rim::SlaveWrap::defTransaction)
   ;

}

