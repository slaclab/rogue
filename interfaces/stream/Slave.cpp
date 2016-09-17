/**
 *-----------------------------------------------------------------------------
 * Title      : Stream interface slave
 * ----------------------------------------------------------------------------
 * File       : Slave.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-09-16
 * Last update: 2016-09-16
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
#include <interfaces/stream/Buffer.h>
#include <interfaces/stream/Frame.h>
#include <boost/make_shared.hpp>

namespace is = interfaces::stream;

//! Class creation
is::SlavePtr is::Slave::create () {
   is::SlavePtr slv = boost::make_shared<is::Slave>();
   return(slv);
}

//! Creator
is::Slave::Slave() { 
   allocMeta_ = 0;
   freeMeta_  = 0xFFFFFFFF;
   totAlloc_  = 0;
}

//! Destructor
is::Slave::~Slave() { }

//! Get allocated memory
uint64_t is::Slave::getAlloc() {
   return(totAlloc_);
}

//! Generate a buffer. Called from master
/*
 * Pass total size required.
 * Pass flag indicating if zero copy buffers are acceptable
 */
is::FramePtr is::Slave::acceptReq ( uint32_t size, bool zeroCopyEn) {
   is::FramePtr  ret;
   uint8_t *     data;
   is::BufferPtr buff;

   ret  = is::Frame::create(zeroCopyEn);

   if ( (data = (uint8_t *)malloc(size)) == NULL ) return(ret);

   buff = is::Buffer::create(getSlave(),data,allocMeta_,size);
   allocMeta_++;
   totAlloc_ += size;

   ret->appendBuffer(buff);

   return(ret);
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
void is::Slave::retBuffer(uint8_t * data, uint32_t meta, uint32_t rawSize) {
   if ( meta == freeMeta_ ) printf("Buffer return with duplicate meta\n");
   freeMeta_ = meta;

   if ( data != NULL ) {
      free(data);
      totAlloc_ -= rawSize;
   }
   else printf("Empty buffer returned\n");
}

//! Return instance as shared pointer
is::SlavePtr is::Slave::getSlave() {
   return(shared_from_this());
}

//! Accept frame
bool is::SlaveWrap::acceptFrame ( is::FramePtr frame ) {
   bool ret;
   bool found;

   found = false;
   ret   = false;

   // Not sure if this is (and release) are ok if calling from python to python
   // It appears we need to lock before calling get_override
   PyGILState_STATE pyState = PyGILState_Ensure();

   if (boost::python::override pb = this->get_override("acceptFrame")) {
      found = true;
      try {
         ret = pb(frame);
      } catch (...) {
         PyErr_Print();
      }
   }
   PyGILState_Release(pyState);

   if ( ! found ) ret = is::Slave::acceptFrame(frame);
   return(ret);
}

//! Default accept frame call
bool is::SlaveWrap::defAcceptFrame ( is::FramePtr frame ) {
   return(is::Slave::acceptFrame(frame));
}

