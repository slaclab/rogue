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
#include <rogue/GeneralError.h>
#include <boost/python.hpp>

namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

ris::FrameIterator::FrameIterator(ris::FramePtr frame, bool write, bool end) {
   write_     = write;
   frame_     = frame;
   frameSize_ = (write_) ? frame_->getSize() : frame_->getPayload();

   if ( end ) framePos_ = frameSize_;
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

   if ( frameSize_ == 0 ) 
      throw rogue::GeneralError("FrameIterator::adjust","Invalid iterator reference!");

   // Increment
   if ( diff > 0 ) {
      if ( (framePos_ + diff) > frameSize_ ) 
         throw rogue::GeneralError("FrameIterator::adjust","Iterator overflow!");

      // Adustment puts us at the end
      if ( (framePos_ + diff) == frameSize_ ) {
         framePos_ = frameSize_;
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

      if ( diff > framePos_ ) 
         throw rogue::GeneralError("FrameIterator::adjust","Iterator underflow!");

      // Frame is at end, rewind and reset position to relative offset
      if ( framePos_ == frameSize_ ) {
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

//! De-reference
uint8_t & ris::FrameIterator::operator *() const {
   if ( framePos_ == frameSize_ ) 
      throw rogue::GeneralError("FrameIterator::*","Invalid iterator reference!");
   else return *data_;
}

//! Pointer
uint8_t * ris::FrameIterator::operator ->() const {
   if ( framePos_ == frameSize_ ) 
      throw rogue::GeneralError("FrameIterator::->","Invalid iterator reference!");
   else return data_;
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

void ris::FrameIterator::setup_python() { }

