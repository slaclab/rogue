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
#include <interfaces/memory/Slave.h>
#include <boost/make_shared.hpp>
#include <interfaces/memory/Block.h>
#include <interfaces/memory/BlockVector.h>

namespace rim = rogue::interfaces::memory;

//! Create a slave container
rim::SlavePtr rim::Slave::create () {
   rim::SlavePtr s = boost::make_shared<rim::Slave>();
   return(s);
}

//! Create object
rim::Slave::Slave() { } 

//! Destroy object
rim::Slave::~Slave() { }

//! Issue a set of write transactions
bool rim::Slave::doWrite (rim::BlockVectorPtr blocks) {
   return(false);
}

//! Issue a set of read transactions
bool rim::Slave::doRead  (rim::BlockVectorPtr blocks) {
   return(false);
}

//! Issue a set of write transactions
bool rim::SlaveWrap::doWrite (rim::BlockVectorPtr blocks) {
   bool ret;
   bool found;

   found = false;
   ret   = false;

   // Not sure if this is (and release) are ok if calling from python to python
   // It appears we need to lock before calling get_override
   PyGILState_STATE pyState = PyGILState_Ensure();

   if (boost::python::override pb = this->get_override("doWrite")) {
      found = true;
      try {
         ret = pb(blocks);
      } catch (...) {
         PyErr_Print();
      }
   }
   PyGILState_Release(pyState);

   if ( ! found ) ret = rim::Slave::doWrite(blocks);
   return(ret);
}

//! Default doWite call
bool rim::SlaveWrap::defDoWrite ( rim::BlockVectorPtr blocks ) {
   return(rim::Slave::doWrite(blocks));
}

//! Issue a set of read transactions
bool rim::SlaveWrap::doRead (rim::BlockVectorPtr blocks) {
   bool ret;
   bool found;

   found = false;
   ret   = false;

   // Not sure if this is (and release) are ok if calling from python to python
   // It appears we need to lock before calling get_override
   PyGILState_STATE pyState = PyGILState_Ensure();

   if (boost::python::override pb = this->get_override("doRead")) {
      found = true;
      try {
         ret = pb(blocks);
      } catch (...) {
         PyErr_Print();
      }
   }
   PyGILState_Release(pyState);

   if ( ! found ) ret = rim::Slave::doRead(blocks);
   return(ret);
}

//! Default accept frame call
bool rim::SlaveWrap::defDoRead ( rim::BlockVectorPtr blocks ) {
   return(rim::Slave::doRead(blocks));
}


