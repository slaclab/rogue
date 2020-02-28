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

   // end iterator
   if ( end ) {
      buff_     = frame_->endBuffer();
      framePos_ = frameSize_;
      buffBeg_  = frameSize_;
      buffEnd_  = frameSize_;
      data_     = NULL;
   }
   else {
      buff_     = frame_->beginBuffer();
      framePos_ = 0;
      buffBeg_  = 0;
      buffEnd_  = (write_) ? (*buff_)->getSize() : (*buff_)->getPayload();
      data_     = (*buff_)->begin();
   }
}

//! increment position
void ris::FrameIterator::increment(int32_t diff) {
   framePos_ += diff;
   data_     += diff;

   // Past end of buffer
   if ( framePos_ >= buffEnd_ ) {

      // Past end of frame
      if ( framePos_ >= frameSize_ ) {
         framePos_ = frameSize_;
         buffBeg_  = frameSize_;
         buffEnd_  = frameSize_;
         buff_     = frame_->endBuffer();
         data_     = NULL;
      }

      // Move forward in buffer chain
      else {

         // Increment current buffer until we find the location of the data position
         // Iterator always contains one extra buffer index
         while ( framePos_ >= buffEnd_ ) {
            buff_++;
            buffBeg_  = buffEnd_;
            buffEnd_ += (write_) ? (*buff_)->getSize() : (*buff_)->getPayload();
         }

         // Set pointer
         data_ = (*buff_)->begin() + (framePos_ - buffBeg_);
      }
   }
}

//! decrement position
void ris::FrameIterator::decrement(int32_t diff) {
   framePos_ += diff;
   data_     += diff;

   // Before start of buffer
   if ( framePos_ < buffBeg_ ) {

      // Before beginning of frame
      if ( framePos_ < 0 ) {
         framePos_ = frameSize_;
         buffBeg_  = frameSize_;
         buffEnd_  = frameSize_;
         buff_     = frame_->endBuffer();
         data_     = NULL;
      }

      // Move backwards in buffer chain
      else {

         // Decrement current buffer until the desired frame position is greater than
         // the bottom of the buffer
         while ( framePos_ < buffBeg_ ) {
            buff_--;
            buffEnd_  = buffBeg_;
            buffBeg_ -= (write_) ? (*buff_)->getSize() : (*buff_)->getPayload();
         }

         // Set pointer
         data_ = (*buff_)->begin() + (framePos_ - buffBeg_);
      }
   }
}

ris::FrameIterator::FrameIterator() {
   write_     = false;
   framePos_  = 0;
   frameSize_ = 0;
   buffBeg_   = 0;
   buffEnd_   = 0;
   data_      = NULL;
}

//! Copy assignment
const ris::FrameIterator ris::FrameIterator::operator=(const ris::FrameIterator &rhs) {
   this->write_     = rhs.write_;
   this->frame_     = rhs.frame_;
   this->framePos_  = rhs.framePos_;
   this->frameSize_ = rhs.frameSize_;
   this->buff_      = rhs.buff_;
   this->buffBeg_   = rhs.buffBeg_;
   this->buffEnd_   = rhs.buffEnd_;
   this->data_      = rhs.data_;
   return *this;
}

//! Get iterator to end of buffer or end of frame, whichever is lower
ris::FrameIterator ris::FrameIterator::endBuffer() {
   ris::FrameIterator ret(*this);
   ret.increment(buffEnd_-framePos_);
   return ret;
}

//! Get remaining bytes in current buffer
uint32_t ris::FrameIterator::remBuffer() {
   return (buffEnd_ - framePos_);
}

//! De-reference
uint8_t & ris::FrameIterator::operator *() const {
   return *data_;
}

//! Pointer
//uint8_t * ris::FrameIterator::operator ->() const {
   //return data_;
//}


//! Pointer
uint8_t * ris::FrameIterator::ptr() const {
   return data_;
}

//! De-reference by index
uint8_t ris::FrameIterator::operator [](const uint32_t offset) const {
   ris::FrameIterator ret(*this);
   ret.increment((int32_t)offset);
   return *ret;
}

//! Increment
const ris::FrameIterator & ris::FrameIterator::operator ++() {
   this->increment(1);
   return *this;
}

//! post Increment
ris::FrameIterator ris::FrameIterator::operator ++(int) {
   ris::FrameIterator ret(*this);
   this->increment(1);
   return ret;
}

//! Decrement
const ris::FrameIterator & ris::FrameIterator::operator --() {
   this->decrement(-1);
   return *this;
}

//! post Decrement
ris::FrameIterator ris::FrameIterator::operator --(int) {
   ris::FrameIterator ret(*this);
   this->decrement(-1);
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
ris::FrameIterator ris::FrameIterator::operator +(const int32_t add) const {
   ris::FrameIterator ret(*this);
   if ( add > 0 ) ret.increment(add);
   else ret.decrement(add);
   return ret;
}

//! Descrment by value
ris::FrameIterator ris::FrameIterator::operator -(const int32_t sub) const {
   ris::FrameIterator ret(*this);
   if ( sub > 0 ) ret.decrement(-1 * sub);
   else ret.increment(-1 * sub);
   return ret;
}

//! Sub incrementers
int32_t ris::FrameIterator::operator -(const ris::FrameIterator &other) const {
   return(this->framePos_ - other.framePos_);
}

//! Increment by value
ris::FrameIterator & ris::FrameIterator::operator +=(const int32_t add) {
   if ( add > 0 ) this->increment(add);
   else this->decrement(add);
   return *this;
}

//! Descrment by value
ris::FrameIterator & ris::FrameIterator::operator -=(const int32_t sub) {
   if ( sub > 0 ) this->decrement(-1 * sub);
   else this->increment(-1 * sub);
   return *this;
}


