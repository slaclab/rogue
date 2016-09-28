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
#include <string>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/exceptions/AllocationException.h>
#include <boost/make_shared.hpp>

namespace ris = rogue::interfaces::stream;
namespace re  = rogue::exceptions;
namespace bp  = boost::python;

//! Class creation
ris::SlavePtr ris::Slave::create () {
   ris::SlavePtr slv = boost::make_shared<ris::Slave>();
   return(slv);
}

//! Creator
ris::Slave::Slave() { 
   allocMeta_  = 0;
   freeMeta_   = 0xFFFFFFFF;
   allocBytes_ = 0;
   allocCount_ = 0;
   debug_      = 0;
}

//! Destructor
ris::Slave::~Slave() { }

//! Set debug message size
void ris::Slave::setDebug(uint32_t debug, std::string name) {
   name_  = name;
   debug_ = debug;
}

//! Get allocated memory
uint32_t ris::Slave::getAllocBytes() {
   return(allocBytes_);
}

//! Get allocated count
uint32_t ris::Slave::getAllocCount() {
   return(allocCount_);
}

//! Create a frame
// Frame container should be allocated from shared memory pool
ris::FramePtr ris::Slave::createFrame ( uint32_t totSize, uint32_t buffSize,
                                        bool compact, bool zeroCopy ) {
   ris::FramePtr  ret;
   ris::BufferPtr buff;
   uint32_t alloc;
   uint32_t bSize;

   ret  = ris::Frame::create(shared_from_this(),zeroCopy);
   alloc = 0;

   while ( alloc < totSize ) {

      // Don't create larger buffers than we need if compact is set
      if ( (compact == false) || ((totSize-alloc) > buffSize) ) bSize = buffSize;
      else bSize = (totSize-alloc);

      // Create buffer and append to frame
      buff = allocBuffer(bSize);
      alloc += bSize;
      ret->appendBuffer(buff);
   }

   return(ret);
}

//! Create a buffer
// Buffer container and raw data should be allocated from shared memory pool
ris::BufferPtr ris::Slave::allocBuffer ( uint32_t size ) {
   ris::BufferPtr buff;
   uint8_t * data;

   if ( (data = (uint8_t *)malloc(size)) == NULL ) 
      throw(re::AllocationException(size));

   buff = createBuffer(data,allocMeta_,size);

   boost::lock_guard<boost::mutex> lock(metaMtx_);

   // Only use lower 16 bits of meta. 
   // Upper 16 bits may have special meaning to sub-class
   allocMeta_++;
   allocMeta_ &= 0xFFFF;

   return(buff);
}


//! Create a Buffer with passed data
ris::BufferPtr ris::Slave::createBuffer( void * data, uint32_t meta, uint32_t rawSize) {
   ris::BufferPtr buff;

   boost::lock_guard<boost::mutex> lock(metaMtx_);

   buff = ris::Buffer::create(shared_from_this(),data,meta,rawSize);

   allocBytes_ += rawSize;
   allocCount_++;
   return(buff);
}

//! Delete a buffer
void ris::Slave::deleteBuffer( uint32_t rawSize) {
   boost::lock_guard<boost::mutex> lock(metaMtx_);
   allocBytes_ -= rawSize;
   allocCount_--;
}

//! Accept a frame request. Called from master
/*
 * Pass total size required.
 * Pass flag indicating if zero copy buffers are acceptable
 */
ris::FramePtr ris::Slave::acceptReq ( uint32_t size, bool zeroCopyEn) {
   return(createFrame(size,size,false,false));
}

//! Accept a frame from master
void ris::Slave::acceptFrame ( ris::FramePtr frame ) {
   uint32_t x;
   uint8_t  val;

   if ( debug_ > 0 ) {
      printf("%s: Got Size=%i, Data:\n",name_.c_str(),frame->getPayload());
      printf("     ");
      for (x=0; (x < debug_ && x < frame->getPayload()); x++) {
         frame->read(&val,x,1);
         printf(" 0x%.2x",val);
         if (( (x+1) % 10 ) == 0) 
            printf("\n     ");
      }
      if (( x % 10 ) != 0) printf("\n");
   }
}

//! Return a buffer
/*
 * Called when this instance is marked as owner of a Buffer entity
 */
void ris::Slave::retBuffer(uint8_t * data, uint32_t meta, uint32_t rawSize) {
   boost::lock_guard<boost::mutex> lock(metaMtx_);
   if ( meta == freeMeta_ ) printf("Buffer return with duplicate meta\n");
   freeMeta_ = meta;

   if ( data != NULL ) free(data);
   allocBytes_ -= rawSize;
   allocCount_--;
}

//! Accept frame
void ris::SlaveWrap::acceptFrame ( ris::FramePtr frame ) {
   bool found;

   found = false;

   // Not sure if this is (and release) are ok if calling from python to python
   // It appears we need to lock before calling get_override
   PyGILState_STATE pyState = PyGILState_Ensure();

   if (boost::python::override pb = this->get_override("acceptFrame")) {
      found = true;
      try {
         pb(frame);
      } catch (...) {
         PyErr_Print();
      }
   }
   PyGILState_Release(pyState);

   if ( ! found ) ris::Slave::acceptFrame(frame);
}

//! Default accept frame call
void ris::SlaveWrap::defAcceptFrame ( ris::FramePtr frame ) {
   ris::Slave::acceptFrame(frame);
}

void ris::Slave::setup_python() {

   bp::class_<ris::SlaveWrap, ris::SlaveWrapPtr, boost::noncopyable>("Slave",bp::init<>())
      .def("create",         &ris::Slave::create)
      .staticmethod("create")
      .def("setDebug",       &ris::Slave::setDebug)
      .def("acceptFrame",    &ris::Slave::acceptFrame, &ris::SlaveWrap::defAcceptFrame)
      .def("getAllocCount",  &ris::Slave::getAllocCount)
      .def("getAllocBytes",  &ris::Slave::getAllocBytes)
   ;
}

