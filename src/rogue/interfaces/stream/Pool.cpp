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
#include <memory>
#include <rogue/GilRelease.h>

namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Creator
ris::Pool::Pool() {
   allocMeta_  = 0;
   allocBytes_ = 0;
   allocCount_ = 0;
   fixedSize_  = 0;
   poolSize_   = 0;
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

//! Accept a frame request. Called from master
/*
 * Pass total size required.
 * Pass flag indicating if zero copy buffers are acceptable
 */
ris::FramePtr ris::Pool::acceptReq (uint32_t size, bool zeroCopyEn) {
   ris::FramePtr ret;
   uint32_t frSize;

   ret  = ris::Frame::create();
   frSize = 0;

   // Buffers may be smaller than frame
   while ( frSize < size ) ret->appendBuffer(allocBuffer(size,&frSize));
   return(ret);
}

//! Return a buffer
/*
 * Called when this instance is marked as owner of a Buffer entity
 */
void ris::Pool::retBuffer(uint8_t * data, uint32_t meta, uint32_t rawSize) {
   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> lock(mtx_);

   if ( data != NULL ) {
      if ( rawSize == fixedSize_ && poolSize_ > dataQ_.size() ) dataQ_.push(data);
      else free(data);
   }
   allocBytes_ -= rawSize;
   allocCount_--;
}

void ris::Pool::setup_python() {
#ifndef NO_PYTHON
   bp::class_<ris::Pool, ris::PoolPtr, boost::noncopyable>("Pool",bp::init<>())
      .def("getAllocCount",  &ris::Pool::getAllocCount)
      .def("getAllocBytes",  &ris::Pool::getAllocBytes)
      .def("setFixedSize",   &ris::Pool::setFixedSize)
      .def("getFixedSize",   &ris::Pool::getFixedSize)
      .def("setPoolSize",    &ris::Pool::setPoolSize)
      .def("getPoolSize",    &ris::Pool::getPoolSize)
   ;
#endif
}

//! Set fixed size mode
void ris::Pool::setFixedSize(uint32_t size) {
   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> lock(mtx_);

   fixedSize_ = size;
}

//! Get fixed size mode
uint32_t ris::Pool::getFixedSize() {
   return fixedSize_;
}

//! Set buffer pool size
void ris::Pool::setPoolSize(uint32_t size) {
   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> lock(mtx_);

   poolSize_ = size;
}

//! Get pool size
uint32_t ris::Pool::getPoolSize() {
   return poolSize_;
}

//! Allocate a buffer passed size
// Buffer container and raw data should be allocated from shared memory pool
ris::BufferPtr ris::Pool::allocBuffer ( uint32_t size, uint32_t *total ) {
   uint8_t * data;
   uint32_t  bAlloc;
   uint32_t  bSize;
   uint32_t  meta = 0;

   bAlloc = size;
   bSize  = size;

   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> lock(mtx_);
   if ( fixedSize_ > 0 ) {
      bAlloc = fixedSize_;
      if ( bSize > bAlloc ) bSize = bAlloc;
   }

   if ( dataQ_.size() > 0 ) {
      data = dataQ_.front();
      dataQ_.pop();
   }
   else if ( (data = (uint8_t *)malloc(bAlloc)) == NULL )
      throw(rogue::GeneralError::create("Pool::allocBuffer","Failed to allocate buffer with size = %i",bAlloc));

   // Only use lower 24 bits of meta.
   // Upper 8 bits may have special meaning to sub-class
   meta = allocMeta_;
   allocMeta_++;
   allocMeta_ &= 0xFFFFFF;
   allocBytes_ += bAlloc;
   allocCount_++;
   if ( total != NULL ) *total += bSize;
   return(ris::Buffer::create(shared_from_this(),data,meta,bSize,bAlloc));
}

//! Create a Buffer with passed data
ris::BufferPtr ris::Pool::createBuffer( void * data, uint32_t meta, uint32_t size, uint32_t alloc) {
   ris::BufferPtr buff;

   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> lock(mtx_);

   buff = ris::Buffer::create(shared_from_this(),data,meta,size,alloc);

   allocBytes_ += alloc;
   allocCount_++;
   return(buff);
}

//! Track buffer deletion
void ris::Pool::decCounter( uint32_t alloc) {
   rogue::GilRelease noGil;
   std::lock_guard<std::mutex> lock(mtx_);
   allocBytes_ -= alloc;
   allocCount_--;
}

