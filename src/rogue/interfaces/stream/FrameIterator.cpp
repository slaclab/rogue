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

ris::FrameIterator::FrameIterator(ris::FramePtr frame, uint32_t offset, bool end) {
   ris::Frame::BufferIterator it;
  
   end_      = end; 
   frame_    = frame;
   curr_     = frame->endBuffer();
   buffPos_  = 0;
   framePos_ = 0;

   if ( ! end ) {
      buffPos_  = offset;
      framePos_ = offset;

      for ( it=frame_->beginBuffer(); it != frame->endBuffer(); ++it ) {
         curr_ = it;

         if ( (*it)->getSize() > buffPos_ ) break;
         else buffPos_ -= (*it)->getSize();
      }
   }
}

ris::FrameIterator::FrameIterator() {
   end_      = false;
   buffPos_  = 0;
   framePos_ = 0;
}

//! Copy assignment
const ris::FrameIterator ris::FrameIterator::operator=(const ris::FrameIterator &rhs) {
   this->end_      = rhs.end_;
   this->frame_    = rhs.frame_;
   this->curr_     = rhs.curr_;
   this->buffPos_  = rhs.buffPos_;
   this->framePos_ = rhs.framePos_;
   return *this;
}

//! De-reference
uint8_t ris::FrameIterator::operator *() const {
   if ( frame_ == NULL ) return 0;
   else if ( end_ ) return 0;
   else return *((*curr_)->begin());
}

//! Pointer
uint8_t * ris::FrameIterator::operator ->() const {
   if ( (frame_ == NULL) || end_ ) return NULL;
   else return (*curr_)->begin();
}

//! De-reference by index
uint8_t ris::FrameIterator::operator [](const uint32_t &offset) const {
   if ( frame_ == NULL ) 
      throw rogue::GeneralError("FrameIterator::[]","Empty iterator");

   if ((offset + framePos_) >= frame_->getSize()) 
      throw rogue::GeneralError("FrameIterator::[]","Ran past end of frame!");

   ris::FrameIterator ret(frame_, (framePos_ + offset),false);
   return *ret;
}

//! Increment
const ris::FrameIterator & ris::FrameIterator::operator ++() {
   if ( frame_ == NULL ) 
      throw rogue::GeneralError("FrameIterator::++","Empty iterator");

   if ( end_ ) throw rogue::GeneralError("FrameIterator::++","Ran past end of frame!");
   ++framePos_;

   if ( ++buffPos_ == (*curr_)->getSize() ) {
      buffPos_ = 0;
      if ( ++curr_ == frame_->endBuffer() ) end_ = true;
   }
   return *this;
}

//! post Increment
ris::FrameIterator ris::FrameIterator::operator ++(int) {
   ris::FrameIterator ret(*this);
   ++(*this);
   return ret;
}

//! Decrement
const ris::FrameIterator & ris::FrameIterator::operator --() {
   if ( frame_ == NULL ) 
      throw rogue::GeneralError("FrameIterator::--","Empty iterator");

   if ( framePos_ == 0 ) throw rogue::GeneralError("FrameIterator::++","Ran past start of frame!");
   --framePos_;

   if ( end_ || buffPos_ == 0 ) {
      curr_--;
      end_ = false;
      buffPos_ = (*curr_)->getSize()-1;
   }
   else --buffPos_;
   return *this;
}

//! post Decrement
ris::FrameIterator ris::FrameIterator::operator --(int) {
   ris::FrameIterator ret(*this);
   --(*this);
   return ret;
}

//! Not Equal
bool ris::FrameIterator::operator !=(const ris::FrameIterator & other) const {
   if ( frame_ == NULL ) 
      throw rogue::GeneralError("FrameIterator::!=","Empty iterator");

   return(other.framePos_ != framePos_ || other.frame_ != frame_);
}

//! Equal
bool ris::FrameIterator::operator ==(const ris::FrameIterator & other) const {
   if ( frame_ == NULL ) 
      throw rogue::GeneralError("FrameIterator::==","Empty iterator");

   return(other.framePos_ == framePos_ && other.frame_ == frame_);
}

//! Less than
bool ris::FrameIterator::operator <(const ris::FrameIterator & other) const {
   if ( frame_ == NULL ) 
      throw rogue::GeneralError("FrameIterator::<","Empty iterator");

   return ( framePos_ < other.framePos_ );
}

//! greater than
bool ris::FrameIterator::operator >(const ris::FrameIterator & other) const {
   if ( frame_ == NULL ) 
      throw rogue::GeneralError("FrameIterator::>","Empty iterator");

   return ( framePos_ > other.framePos_ );
}

//! Less than equal
bool ris::FrameIterator::operator <=(const ris::FrameIterator & other) const {
   if ( frame_ == NULL ) 
      throw rogue::GeneralError("FrameIterator::<=","Empty iterator");

   return ( framePos_ <= other.framePos_ );
}

//! greater than equal
bool ris::FrameIterator::operator >=(const ris::FrameIterator & other) const {
   if ( frame_ == NULL ) 
      throw rogue::GeneralError("FrameIterator::>=","Empty iterator");

   return ( framePos_ >= other.framePos_ );
}

//! Increment by value, this can be done better
ris::FrameIterator ris::FrameIterator::operator +(const int32_t &add) const {
   if ( frame_ == NULL ) 
      throw rogue::GeneralError("FrameIterator::+","Empty iterator");

   ris::FrameIterator ret(*this);
   int32_t loc = add;

   if ( loc > 0 ) while ( --loc >= 0 ) ++ret;
   else if ( loc < 0 ) while ( ++loc >= 0 ) --ret;

   return ret;
}

//! Descrment by value, this can be done better
ris::FrameIterator ris::FrameIterator::operator -(const int32_t &sub) const {
   if ( frame_ == NULL ) 
      throw rogue::GeneralError("FrameIterator::-","Empty iterator");

   ris::FrameIterator ret(*this);
   int32_t loc = sub;

   if ( loc > 0 ) while ( --loc >= 0 ) --ret;
   else if ( loc < 0 ) while ( ++loc >= 0 ) ++ret;

   return ret;
}

//! Sub incrementers
int32_t ris::FrameIterator::operator -(const ris::FrameIterator &other) const {
   if ( frame_ == NULL ) 
      throw rogue::GeneralError("FrameIterator::-","Empty iterator");

   return(framePos_ - other.framePos_);
}

//! Increment by value, this can be done better
ris::FrameIterator & ris::FrameIterator::operator +=(const int32_t &add) {
   if ( frame_ == NULL ) 
      throw rogue::GeneralError("FrameIterator::+=","Empty iterator");

   int32_t loc = add;
   if ( loc > 0 ) while ( --loc >= 0 ) ++(*this);
   else if ( loc < 0 ) while ( ++loc >= 0 ) --(*this);

   return *this;
}

//! Descrment by value, this can be done better
ris::FrameIterator & ris::FrameIterator::operator -=(const int32_t &sub) {
   if ( frame_ == NULL ) 
      throw rogue::GeneralError("FrameIterator::-=","Empty iterator");

   int32_t loc = sub;
   if ( loc > 0 ) while ( --loc >= 0 ) --(*this);
   else if ( loc < 0 ) while ( ++loc >= 0 ) ++(*this);

   return *this;
}

void ris::FrameIterator::setup_python() { }

