/**
 *-----------------------------------------------------------------------------
 * Title      : Stream Buffer Container
 * ----------------------------------------------------------------------------
 * File       : Buffer.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-09-16
 * Last update: 2016-09-16
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

#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/interfaces/stream/Pool.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/GeneralError.h>
#include <memory>

namespace ris = rogue::interfaces::stream;

//! Class creation
/*
 * Pass owner, raw data buffer, and meta data
 */
ris::BufferPtr ris::Buffer::create ( ris::PoolPtr source, void * data, uint32_t meta, uint32_t size, uint32_t alloc) {
   ris::BufferPtr buff = std::make_shared<ris::Buffer>(source,data,meta,size,alloc);
   return(buff);
}

//! Create a buffer.
/*
 * Pass owner, raw data buffer, and meta data
 */
ris::Buffer::Buffer(ris::PoolPtr source, void *data, uint32_t meta, uint32_t size, uint32_t alloc) {
   source_    = source;
   data_      = (uint8_t *)data;
   meta_      = meta;
   rawSize_   = size;
   allocSize_ = alloc;
   headRoom_  = 0;
   tailRoom_  = 0;
   payload_   = 0;
}

//! Destroy a buffer
/*
 * Owner return buffer method is called
 */
ris::Buffer::~Buffer() {
   source_->retBuffer(data_,meta_,allocSize_);
}

//! Set container frame
void ris::Buffer::setFrame(ris::FramePtr frame) {
   frame_ = frame;
}

//! Get meta data, used by pool
uint32_t ris::Buffer::getMeta() {
   return(meta_);
}

//! Set meta data, used by pool
void ris::Buffer::setMeta(uint32_t meta) {
   meta_ = meta;
}

//! Adjust header by passed value
void ris::Buffer::adjustHeader(int32_t value) {

   // Decreasing header size
   if ( value < 0 && (uint32_t)abs(value) > headRoom_ )
         throw(rogue::GeneralError::create("Buffer::adjustHeader",
                  "Attempt to reduce header with size %i by %i",headRoom_,value));

   // Increasing header size
   if ( value > 0 && (uint32_t)value > (rawSize_ - (headRoom_ + tailRoom_)) )
         throw(rogue::GeneralError::create("Buffer::adjustHeader",
                  "Attempt to increase header by %i in buffer with size %i",
                  value, (rawSize_ - (headRoom_ + tailRoom_))));

   // Make adjustment
   headRoom_ += value;

   // Payload can never be less than headroom
   if ( payload_ < headRoom_ ) payload_ = headRoom_;

   ris::FramePtr tmpPtr;
   if ( (tmpPtr = frame_.lock()) ) tmpPtr->setSizeDirty();
}

//! Clear the header reservation
void ris::Buffer::zeroHeader() {
   headRoom_ = 0;

   ris::FramePtr tmpPtr;
   if ( (tmpPtr = frame_.lock()) ) tmpPtr->setSizeDirty();
}

//! Adjust tail by passed value
void ris::Buffer::adjustTail(int32_t value) {

   // Decreasing tail size
   if ( value < 0 && (uint32_t)abs(value) > tailRoom_ )
         throw(rogue::GeneralError::create("Buffer::adjustTail",
                  "Attempt to reduce tail with size %i by %i",tailRoom_,value));

   // Increasing tail size
   if ( value > 0 && (uint32_t)value > (rawSize_ - (headRoom_ + tailRoom_)) )
         throw(rogue::GeneralError::create("Buffer::adjustTail",
                  "Attempt to increase header by %i in buffer with size %i",
                  value, (rawSize_ - (headRoom_ + tailRoom_))));

   // Make adjustment
   tailRoom_ += value;

   ris::FramePtr tmpPtr;
   if ( (tmpPtr = frame_.lock()) ) tmpPtr->setSizeDirty();
}

//! Clear the tail reservation
void ris::Buffer::zeroTail() {
   tailRoom_ = 0;

   ris::FramePtr tmpPtr;
   if ( (tmpPtr = frame_.lock()) ) tmpPtr->setSizeDirty();
}

/*
 * Get data pointer (begin iterator)
 * Returns base + header size
 */
uint8_t * ris::Buffer::begin() {
   return(data_ + headRoom_);
}

/*
 * Get end data pointer (end iterator)
 * This is the end of raw data buffer
 */
uint8_t * ris::Buffer::end() {
   return(data_ + (rawSize_-tailRoom_));
}

/*
 * Get end payload pointer (end iterator)
 * This is the end of payload data
 */
uint8_t * ris::Buffer::endPayload() {
   return(data_ + payload_);
}

/*
 * Get size of buffer that can hold
 * payload data. This function
 * returns the full buffer size minus
 * the head and tail reservation.
 */
uint32_t ris::Buffer::getSize() {
   return(rawSize_ - (headRoom_ + tailRoom_));
}

/*
 * Get available size for payload
 * This is the space remaining for payload
 * minus the space reserved for the tail
 */
uint32_t ris::Buffer::getAvailable() {
   uint32_t ret;

   ret = rawSize_ - payload_;

   // Subtract tail space, avoid overflow
   if ( ret < tailRoom_ ) ret = 0;
   else ret -= tailRoom_;

   return(ret);
}

/*
 * Get real payload size without header
 * This is the count of real data in the
 * packet, minus the portion reserved for
 * the head.
 */
uint32_t ris::Buffer::getPayload() {
   return(payload_ - headRoom_);
}

//! Set payload size (not including header)
void ris::Buffer::setPayload(uint32_t size) {
   if ( size > (rawSize_ - (headRoom_ + tailRoom_) ) )
      throw(rogue::GeneralError::create("Buffer::setPayload",
               "Attempt to set payload to size %i in buffer with size %i",
               size, (rawSize_ - (headRoom_ + tailRoom_))));

   payload_ = size + headRoom_;

   ris::FramePtr tmpPtr;
   if ( (tmpPtr = frame_.lock()) ) tmpPtr->setSizeDirty();
}

/*
 * Set min payload size (not including header)
 * Payload size is updated only if size > current size
*/
void ris::Buffer::minPayload(uint32_t size) {
   if ( size > getPayload() ) setPayload(size);
}

//! Adjust payload size
void ris::Buffer::adjustPayload(int32_t value) {
   if ( value < 0 && (uint32_t)abs(value) > getPayload())
      throw(rogue::GeneralError::create("Buffer::adjustPayload",
               "Attempt to decrease payload by %i in buffer with size %i",
               value, getPayload()));

   setPayload(getPayload() + value);
}

//! Set the buffer as full (minus tail reservation)
void ris::Buffer::setPayloadFull() {
   payload_ = rawSize_ - tailRoom_;

   ris::FramePtr tmpPtr;
   if ( (tmpPtr = frame_.lock()) ) tmpPtr->setSizeDirty();
}

//! Set the buffer as empty (minus header reservation)
void ris::Buffer::setPayloadEmpty() {
   payload_ = headRoom_;

   ris::FramePtr tmpPtr;
   if ( (tmpPtr = frame_.lock()) ) tmpPtr->setSizeDirty();
}

//! Debug buffer
void ris::Buffer::debug(uint32_t idx) {
   printf("    Buffer: %i, AllocSize: %i, RawSize: %i, HeadRoom: %i, TailRoom: %i, Payload: %i\n",
         idx, allocSize_, rawSize_, headRoom_, tailRoom_, payload_);
}

