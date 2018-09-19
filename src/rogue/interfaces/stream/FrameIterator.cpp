/**
 *-----------------------------------------------------------------------------
 * Title      : Stream iterator container
 * ----------------------------------------------------------------------------
 * File       : FrameIterator.h
 * Created    : 2018-03-06
 * ----------------------------------------------------------------------------
 * Description:
 * Stream frame iterator
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
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/FrameIterator.h>
#include <rogue/interfaces/stream/Buffer.h>

namespace ris = rogue::interfaces::stream;

ris::FrameIterator::FrameIterator(ris::FramePtr frame, bool write, bool end) {
   write_     = write;
   frame_     = frame;
   frameSize_ = (write_) ? frame_->getSize() : frame_->getPayload();

   // Invalid or end
   if ( end || frameSize_ == 0 ) {
      framePos_ = frameSize_;
      data_     = NULL;
   }
   else {
      framePos_  = 0;
      buffPos_   = 0;
      buff_      = frame_->beginBuffer();
      buffSize_  = (write_) ? (*buff_)->getSize() : (*buff_)->getPayload();
      data_      = (*buff_)->begin();
   }
}

//! adjust position
void ris::FrameIterator::adjust(int32_t diff) {

   // Increment
   if ( diff > 0 ) {

      // Adustment puts us at the end, or overflow
      if ( (framePos_ + diff) >= frameSize_ ) {
         framePos_ = frameSize_;
         data_ = NULL;
         diff = 0;
      }

      // Iterate through increments
      while ( diff > 0 ) {

         // Jump to next buffer
         if ( (buffPos_ + diff) >= buffSize_ ) {
            framePos_ += (buffSize_ - buffPos_);
            diff -= (buffSize_ - buffPos_);
            buff_++;
            buffPos_ = 0;
            buffSize_ = (write_) ? (*buff_)->getSize() : (*buff_)->getPayload();
            data_ = (*buff_)->begin();
         } 
         
         // Adjust within buffer 
         else {
            framePos_ += diff;
            buffPos_ += diff;
            data_ += diff;
            diff = 0;
         }
      } 
   }

   // Decrement
   else if ( diff < 0 ) {

      // Invert
      diff *= -1;

      // Underflow
      if ( diff > framePos_ ) {
         framePos_ = frameSize_;
         data_ = NULL;
         diff = 0;
      }

      // Frame is at end, rewind and reset position to relative offset
      else if ( framePos_ == frameSize_ ) {
         framePos_  = 0;
         buffPos_   = 0;
         buff_      = frame_->beginBuffer();
         buffSize_  = (write_) ? (*buff_)->getSize() : (*buff_)->getPayload();
         data_      = (*buff_)->begin();
         this->adjust(frameSize_ - diff); // Recursion
         diff = 0;
      }

      // Iterate through decrements
      while ( diff > 0 ) {

         // Jump to previous buffer
         if ( diff > buffPos_ ) {
            framePos_ -= (buffPos_ + 1);
            diff -= (buffPos_ + 1);
            buff_--;
            buffSize_  = (write_) ? (*buff_)->getSize() : (*buff_)->getPayload();
            buffPos_ = buffSize_-1;
            data_ = (*buff_)->begin() + buffPos_;
         }
         
         // Adjust within buffer 
         else {
            framePos_ -= diff;
            buffPos_ -= diff;
            data_ -= diff;
            diff = 0;
         }
      }
   }
}

ris::FrameIterator::FrameIterator() {
   write_     = false;
   framePos_  = 0;
   frameSize_ = 0;
   buffPos_   = 0;
   buffSize_  = 0;
   data_      = NULL;
}

//! Copy assignment
const ris::FrameIterator ris::FrameIterator::operator=(const ris::FrameIterator &rhs) {
   this->write_     = rhs.write_;
   this->frame_     = rhs.frame_;
   this->framePos_  = rhs.framePos_;
   this->frameSize_ = rhs.frameSize_;
   this->buff_      = rhs.buff_;
   this->buffPos_   = rhs.buffPos_;
   this->buffSize_  = rhs.buffSize_;
   this->data_      = rhs.data_;
   return *this;
}

//! Get iterator to end of buffer or end of frame, whichever is lower
ris::FrameIterator ris::FrameIterator::endBuffer() {
   ris::FrameIterator ret(*this);
   ret.adjust(buffSize_-buffPos_);
   return ret;
}

//! Get remaining bytes in current buffer
uint32_t ris::FrameIterator::remBuffer() {
   if ( framePos_ == frameSize_ ) return(0);
   else return (buffSize_-buffPos_);
}

//! De-reference
uint8_t & ris::FrameIterator::operator *() const {
   return *data_;
}

//! Pointer
uint8_t * ris::FrameIterator::operator ->() const {
   return data_;
}


//! Pointer
uint8_t * ris::FrameIterator::ptr() const {
   return data_;
}

//! De-reference by index
uint8_t ris::FrameIterator::operator [](const uint32_t &offset) const {
   ris::FrameIterator ret(*this);
   ret.adjust((int32_t)offset);
   return *ret;
}

//! Increment
const ris::FrameIterator & ris::FrameIterator::operator ++() {
   this->adjust(1);
   return *this;
}

//! post Increment
ris::FrameIterator ris::FrameIterator::operator ++(int) {
   ris::FrameIterator ret(*this);
   ret.adjust(1);
   return ret;
}

//! Decrement
const ris::FrameIterator & ris::FrameIterator::operator --() {
   this->adjust(-1);
   return *this;
}

//! post Decrement
ris::FrameIterator ris::FrameIterator::operator --(int) {
   ris::FrameIterator ret(*this);
   ret.adjust(-1);
   return ret;
}

//! Not Equal
bool ris::FrameIterator::operator !=(const ris::FrameIterator & other) const {
   return(this->framePos_ != other.framePos_);
}

//! Equal
bool ris::FrameIterator::operator ==(const ris::FrameIterator & other) const {
   return(this->framePos_ == other.framePos_);
}

//! Less than
bool ris::FrameIterator::operator <(const ris::FrameIterator & other) const {
   return(this->framePos_ < other.framePos_);
}

//! greater than
bool ris::FrameIterator::operator >(const ris::FrameIterator & other) const {
   return(this->framePos_ > other.framePos_);
}

//! Less than equal
bool ris::FrameIterator::operator <=(const ris::FrameIterator & other) const {
   return(this->framePos_ <= other.framePos_);
}

//! greater than equal
bool ris::FrameIterator::operator >=(const ris::FrameIterator & other) const {
   return(this->framePos_ >= other.framePos_);
}

//! Increment by value
ris::FrameIterator ris::FrameIterator::operator +(const int32_t &add) const {
   ris::FrameIterator ret(*this);
   ret.adjust(add);
   return ret;
}

//! Descrment by value
ris::FrameIterator ris::FrameIterator::operator -(const int32_t &sub) const {
   ris::FrameIterator ret(*this);
   ret.adjust(-sub);
   return ret;
}

//! Sub incrementers
int32_t ris::FrameIterator::operator -(const ris::FrameIterator &other) const {
   return(this->framePos_ - other.framePos_);
}

//! Increment by value
ris::FrameIterator & ris::FrameIterator::operator +=(const int32_t &add) {
   this->adjust(add);
   return *this;
}

//! Descrment by value
ris::FrameIterator & ris::FrameIterator::operator -=(const int32_t &sub) {
   this->adjust(-sub);
   return *this;
}


