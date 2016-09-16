/**
 *-----------------------------------------------------------------------------
 * Title      : Stream Buffer Container
 * ----------------------------------------------------------------------------
 * File       : StreamBuffer.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-08-08
 * Last update: 2016-08-08
 * ----------------------------------------------------------------------------
 * Description:
 * Stream frame container
 * Some concepts borrowed from CPSW by Till Straumann
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

#include <interfaces/stream/Buffer.h>
#include <interfaces/stream/Slave.h>
#include <boost/make_shared.hpp>

namespace is = interfaces::stream;

//! Class creation
/*
 * Pass owner, raw data buffer, and meta data
 */
is::BufferPtr is::Buffer::create ( is::SlavePtr source, void * data, uint32_t meta, uint32_t rawSize) {
   is::BufferPtr buff = boost::make_shared<is::Buffer>(source,data,meta,rawSize);
   return(buff);
}

//! Create a buffer.
/*
 * Pass owner, raw data buffer, and meta data
 */
is::Buffer::Buffer(is::SlavePtr source, void *data, uint32_t meta, uint32_t rawSize) {
   source_   = source;
   data_     = (uint8_t *)data;
   meta_     = meta;
   rawSize_  = rawSize;
   headRoom_ = 0;
   count_    = 0;
   error_    = 0;
}

//! Destroy a buffer
/*
 * Owner return buffer method is called
 */
is::Buffer::~Buffer() {
   source_->retBuffer(data_,meta_,rawSize_);
}

//! Get raw data pointer
uint8_t * is::Buffer::getRawData() {
   return(data_);
}

//! Get payload data pointer
uint8_t * is::Buffer::getPayloadData() {
   if ( data_ == NULL ) return(NULL);
   else return(data_ + headRoom_);
}

//! Get meta data
uint32_t is::Buffer::getMeta() {
   return(meta_);
}

//! Get raw size
uint32_t is::Buffer::getRawSize() {
   return(rawSize_);
}

//! Get header space
uint32_t is::Buffer::getHeadRoom() {
   return(headRoom_);
}

//! Get available size for payload
uint32_t is::Buffer::getAvailable() {
   uint32_t temp;

   temp = rawSize_ - count_;

   if ( temp < headRoom_) return(0);
   else return(temp - headRoom_);
}

//! Get real payload size
uint32_t is::Buffer::getPayload() {
   if ( count_ < headRoom_ ) return(0);
   else return(count_ - headRoom_);
}

//! Get error state
uint32_t is::Buffer::getError() {
   return(error_);
}

//! Set error state
void is::Buffer::setError(uint32_t error) {
   error_ = error;
}

//! Set size including header
void is::Buffer::setSetSize(uint32_t size) {
   count_ = size;
}

//! Set head room
void is::Buffer::setHeadRoom(uint32_t offset) {
   headRoom_ = offset;
}

//! Read up to count bytes from buffer, starting from offset.
uint32_t is::Buffer::read  ( void *p, uint32_t offset, uint32_t count ) {
   uint32_t rcnt;

   // Empty buffer
   if ( data_ == NULL ) return(0);

   // No data in buffer
   if ( count_ < headRoom_ ) return(0);

   // Read offset is larger than payload
   if ( offset >= (count_ - headRoom_) ) return(0);

   // Adjust read count for payload size and offset
   if ( count > ((count_ - headRoom_) - offset) ) 
      rcnt = ((count_ - headRoom_) - offset);
   else rcnt = count;

   // Copy data
   memcpy(p,data_+headRoom_+offset,rcnt);
   return(rcnt);
}

//! Write count bytes to frame, starting at offset
uint32_t is::Buffer::write ( void *p, uint32_t offset, uint32_t count ) {
   uint32_t wcnt;

   // Empty buffer
   if ( data_ == NULL ) return(0);

   if ( offset >= (rawSize_ - headRoom_) ) return(0);

   if ( count > ((rawSize_ - headRoom_) - offset)) 
      wcnt = ((rawSize_ - headRoom_) - offset);
   else wcnt = count;

   // Set payload size to last write
   count_ = offset + headRoom_ + wcnt;
   memcpy(data_+headRoom_+offset,p,wcnt);
   return(wcnt);
}

