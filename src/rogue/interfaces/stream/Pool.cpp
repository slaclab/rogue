/**
 *-----------------------------------------------------------------------------
 * Title      : Stream memory pool
 * ----------------------------------------------------------------------------
 * File       : Pool.cpp
 * Created    : 2016-09-16
 * ----------------------------------------------------------------------------
 * Description:
 * Stream memory pool
 *    The function calls in this are a mess! create buffer, allocate buffer, etc
 *    need to be reworked.
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
#include <rogue/interfaces/stream/Pool.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <rogue/common.h>

namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Creator
ris::Pool::Pool() { 
   allocMeta_  = 0;
   freeMeta_   = 0xFFFFFFFF;
   allocBytes_ = 0;
   allocCount_ = 0;
}

//! Destructor
ris::Pool::~Pool() { }

//! Get allocated memory
uint32_t ris::Pool::getAllocBytes() {
   return(allocBytes_);
}

//! Get allocated count
uint32_t ris::Pool::getAllocCount() {
   return(allocCount_);
}

//! Create a frame and allocate buffers
// Frame container should be allocated from shared memory pool
ris::FramePtr ris::Pool::createFrame ( uint32_t totSize, uint32_t buffSize,
                                        bool compact, bool zeroCopy ) {
   ris::FramePtr  ret;
   ris::BufferPtr buff;
   uint32_t alloc;
   uint32_t bSize;

   if ( buffSize == 0 ) buffSize = totSize;

   ret  = ris::Frame::create();
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

//! Allocate a buffer passed size
// Buffer container and raw data should be allocated from shared memory pool
ris::BufferPtr ris::Pool::allocBuffer ( uint32_t size ) {
   uint8_t * data;
   uint32_t  meta;

   if ( (data = (uint8_t *)malloc(size)) == NULL ) 
      throw(rogue::GeneralError::allocation("Pool::allocBuffer",size));

   // Temporary lock to get meta
   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::lock_guard<boost::mutex> lock(mtx_);

      // Only use lower 24 bits of meta. 
      // Upper 8 bits may have special meaning to sub-class
      meta = allocMeta_;
      allocMeta_++;
      allocMeta_ &= 0xFFFFFF;
   }
   PyRogue_END_ALLOW_THREADS;

   return(createBuffer(data,meta,size));
}

//! Create a Buffer with passed data
ris::BufferPtr ris::Pool::createBuffer( void * data, uint32_t meta, uint32_t rawSize) {
   ris::BufferPtr buff;

   PyRogue_BEGIN_ALLOW_THREADS;
   {

      boost::lock_guard<boost::mutex> lock(mtx_);

      buff = ris::Buffer::create(shared_from_this(),data,meta,rawSize);

      allocBytes_ += rawSize;
      allocCount_++;
   }
   PyRogue_END_ALLOW_THREADS;

   return(buff);
}

//! Track buffer deletion
void ris::Pool::deleteBuffer( uint32_t rawSize) {
   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::lock_guard<boost::mutex> lock(mtx_);
      allocBytes_ -= rawSize;
      allocCount_--;
   }
   PyRogue_END_ALLOW_THREADS;
}

//! Accept a frame request. Called from master
/*
 * Pass total size required.
 * Pass flag indicating if zero copy buffers are acceptable
 */
ris::FramePtr ris::Pool::acceptReq ( uint32_t size, bool zeroCopyEn, uint32_t maxBuffSize) {
   return(createFrame(size,maxBuffSize,false,false));
}

//! Return a buffer
/*
 * Called when this instance is marked as owner of a Buffer entity
 */
void ris::Pool::retBuffer(uint8_t * data, uint32_t meta, uint32_t rawSize) {

   if ( meta == freeMeta_ ) 
      throw(rogue::GeneralError("Pool::retBuffer","Buffer return with duplicate meta"));

   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::lock_guard<boost::mutex> lock(mtx_);
      freeMeta_ = meta;

      if ( data != NULL ) free(data);
      allocBytes_ -= rawSize;
      allocCount_--;
   }
   PyRogue_END_ALLOW_THREADS;
}

void ris::Pool::setup_python() {

   bp::class_<ris::Pool, ris::PoolPtr, boost::noncopyable>("Pool",bp::init<>())
      .def("getAllocCount",  &ris::Pool::getAllocCount)
      .def("getAllocBytes",  &ris::Pool::getAllocBytes)
   ;
}

