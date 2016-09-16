/**
 *-----------------------------------------------------------------------------
 * Title      : Stream interface slave
 * ----------------------------------------------------------------------------
 * File       : Slave.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-08-08
 * Last update: 2016-08-08
 * ----------------------------------------------------------------------------
 * Description:
 * Stream interface slave
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
#include <unistd.h>
#include <interfaces/stream/Slave.h>
#include <interfaces/stream/Master.h>
#include <interfaces/stream/Frame.h>

namespace is = interfaces::stream;

//! Creator
is::Slave::Slave() {}

//! Destructor
is::Slave::~Slave() { }

//! Generate a buffer. Called from master
/*
 * Pass total size required.
 * Pass flag indicating if zero copy buffers are acceptable
 */
is::FramePtr is::Slave::acceptReq ( uint32_t size, bool zeroCopyEn) {
   is::FramePtr p;
   return(p);
}

//! Accept a frame from master
/* 
 * Returns true on success
 */
bool is::Slave::acceptFrame ( is::FramePtr frame ) {
   return(false);
}

//! Return a buffer
/*
 * Called when this instance is marked as owner of a Buffer entity
 */
void retBuffer(uint8_t * data, uint32_t meta, uint32_t rawSize) {}

//! Return instance as shared pointer
is::SlavePtr is::Slave::getSlave() {
   return(shared_from_this());
}

//! Accept frame
bool is::SlaveWrap::acceptFrame ( is::FramePtr frame ) {
   bool ret;

   if (boost::python::override pb = this->get_override("acceptFrame")) {

      // Not sure if this is (and release) are ok if calling from python to python
      PyGILState_STATE pyState = PyGILState_Ensure();

      try {
         ret = pb(frame);
      } catch (...) {
         PyErr_Print();
         ret = false;
      }

      PyGILState_Release(pyState);
   }
   else ret = is::Slave::acceptFrame(frame);
   return(ret);
}

//! Default accept frame call
bool is::SlaveWrap::defAcceptFrame ( is::FramePtr frame ) {
   return(is::Slave::acceptFrame(frame));
}


