/**
 *-----------------------------------------------------------------------------
 * Title         : PRBS Receive And Transmit Class
 * ----------------------------------------------------------------------------
 * File          : Prbs.cpp
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 09/17/2016
 * Last update   : 09/17/2016
 *-----------------------------------------------------------------------------
 * Description :
 *    Class used to generate and receive PRBS test data.
 *-----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to 
 * the license terms in the LICENSE.txt file found in the top-level directory 
 * of this distribution and at: 
    * https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
 * No part of the rogue software platform, including this file, may be 
 * copied, modified, propagated, or distributed except according to the terms 
 * contained in the LICENSE.txt file.
 *-----------------------------------------------------------------------------
**/
#include <unistd.h>
#include <stdarg.h>
#include <interfaces/stream/Slave.h>
#include <interfaces/stream/Master.h>
#include <interfaces/stream/Frame.h>
#include <interfaces/stream/Buffer.h>
#include <utilities/Prbs.h>
#include <boost/make_shared.hpp>

namespace ris = rogue::interfaces::stream;
namespace ru  = rogue::utilities;

//! Class creation
ru::PrbsPtr ru::Prbs::create () {
   ru::PrbsPtr p = boost::make_shared<ru::Prbs>();
   return(p);
}

//! Creator with width and variable taps
ru::Prbs::Prbs(uint32_t width, uint32_t tapCnt, ... ) {
   va_list a_list;
   uint32_t   x;

   init(width,tapCnt);

   va_start(a_list,tapCnt);
   for(x=0; x < tapCnt; x++) taps_[x] = va_arg(a_list,uint32_t);
   va_end(a_list);
}

//! Creator with default taps and size
ru::Prbs::Prbs() {
   init(32,4);

   taps_[0] = 1;
   taps_[1] = 2;
   taps_[2] = 6;
   taps_[3] = 31;
}

//! Deconstructor
ru::Prbs::~Prbs() {
   free(taps_);
}

void ru::Prbs::init(uint32_t width, uint32_t tapCnt) {
   sequence_   = 0;
   width_      = width;
   tapCnt_     = tapCnt;
   errCount_   = 0;
   totCount_   = 0;
   totBytes_   = 0;
   thread_     = NULL;
   enMessages_ = false;

   taps_ = (uint32_t *)malloc(sizeof(uint32_t)*tapCnt_);
}

uint32_t ru::Prbs::flfsr(uint32_t input) {
   uint32_t bit = 0;
   uint32_t x;

   for (x=0; x < tapCnt_; x++) bit = bit ^ (input >> taps_[x]);

   bit = bit & 1;

   return ((input << 1) | bit);
}

//! Thread background
void ru::Prbs::runThread() {
   try {
      while(1) {
         genFrame(txSize_);
         boost::this_thread::interruption_point();
      }
   } catch (boost::thread_interrupted&) {}
}

//! Auto run data generation
void ru::Prbs::enable(uint32_t size) {
   if ( thread_ == NULL ) {
      txSize_ = size;
      thread_ = new boost::thread(boost::bind(&Prbs::runThread, this));
   }
}

//! Disable auto generation
void ru::Prbs::disable() {
   if ( thread_ != NULL ) {
      thread_->interrupt();
      thread_->join();
      delete thread_;
      thread_ = NULL;
   }
}

//! Get errors
uint32_t ru::Prbs::getErrors() {
   return(errCount_);
}

//! Get rx/tx count
uint32_t ru::Prbs::getCount() {
   return(totCount_);
}

//! Get total bytes
uint32_t ru::Prbs::getBytes() {
   return(totBytes_);
}

//! Reset counters
// Counters should really be locked!
void ru::Prbs::resetCount() {
   errCount_ = 0;
   totCount_ = 0;
   totBytes_ = 0;
}

//! Enable messages
void ru::Prbs::enMessages(bool state) {
   enMessages_ = state;
}

//! Generate a data frame
void ru::Prbs::genFrame (uint32_t size) {
   uint32_t   word;
   uint32_t   value;
   uint32_t   data32[2];
   uint16_t * data16;
   uint32_t   cnt;

   ris::FramePtr fr = reqFrame(size,true,0);

   if (fr->getAvailable() == 0 ) {
      if ( enMessages_ ) fprintf(stderr,"Prbs::genFrame -> Buffer allocation error, count=%i\n",totCount_);
      errCount_++;
      return;
   }

   data16 = (uint16_t *)data32;
   value = sequence_;
   cnt = 0;

   if ( width_ == 16 ) {
      if ((( size % 2 ) != 0) || size < 6 ) return;
      data16[0] = sequence_ & 0xFFFF;
      data16[1] = (size - 2) / 2;
      cnt += fr->write(data16,0,4);
   }
   else if ( width_ == 32 ) {
      if ((( size % 4 ) != 0) || size < 12 ) return;
      data32[0] = sequence_;
      data32[1] = (size - 4) / 4;
      cnt += fr->write(data32,0,8);
   }
   else {
      if ( enMessages_ ) fprintf(stderr,"Prbs::genFrame -> Bad gen width = %i\n",width_);
      return;
   }

   for (word = 2; word < size/(width_/8); word++) {
      value = flfsr(value);
      if      ( width_ == 16 ) cnt += fr->write(&value,word*2,2);
      else if ( width_ == 32 ) cnt += fr->write(&value,word*4,4);
   }

   if      ( width_ == 16 ) sequence_ = data16[0] + 1;
   else if ( width_ == 32 ) sequence_ = data32[0] + 1;

   totCount_++;
   totBytes_ += size;
   sendFrame(fr,0);
}

//! Accept a frame from master
bool ru::Prbs::acceptFrame ( ris::FramePtr frame, uint32_t timeout ) {
   uint32_t   eventLength;
   uint32_t   expected;
   uint32_t   got;
   uint32_t   word;
   uint32_t   min;
   uint32_t   data32[2];
   uint16_t * data16;
   uint32_t   size;

   data16 = (uint16_t *)data32;

   if ( width_ == 16 ) min = 6;
   else if ( width_ == 32 ) min = 12;
   else {
      if ( enMessages_ ) fprintf(stderr,"Prbs::acceptFrame -> Bad process width = %i\n",width_);
      errCount_++;
      return(false);
   }

   size = frame->getPayload();

   if (size < min ) {
      if ( enMessages_ ) fprintf(stderr,"Prbs::acceptFrame -> Min size violation size=%i, min=%in, count=%i",size,min,totCount_);
      errCount_++;
      return(false);
   }

   totCount_++;
   totBytes_ += size;

   if ( width_ == 16 ) {
      frame->read(data16,0,4);
      expected    = data16[0];
      eventLength = (data16[1] * 2) + 2;
   }
   else if ( width_ == 32 ) {
      frame->read(data16,0,8);
      expected    = data32[0];
      eventLength = (data32[1] * 4) + 4;
   }
   else {
      expected    = 0;
      eventLength = 0;
   }

   if (size < min || eventLength != size) {
      if ( enMessages_ ) 
         fprintf(stderr,"Prbs::acceptFrame -> Bad size. exp=%i, got=%i, count=%i\n",eventLength,size,totCount_);
      errCount_++;
      return(false);
   }

   if ( sequence_ != 0 && sequence_ != expected ) {
      if ( enMessages_ ) 
         fprintf(stderr,"Prbs::acceptFrame -> Bad Sequence. exp=%i, got=%i, count=%i\n",sequence_,expected,totCount_);
      sequence_ = expected + 1;
      errCount_++;
      return(false);
   }
   sequence_ = expected + 1;

   for (word = 2; word < size/(width_/8); word++) {
      expected = flfsr(expected);

      if      ( width_ == 16 ) frame->read(&got,word*2,2);
      else if ( width_ == 32 ) frame->read(&got,word*4,4);
      else got = 0;

      if (expected != got) {
         if ( enMessages_ ) 
            fprintf(stderr,"Prbs::acceptFrame -> Bad value at index %i. exp=0x%x, got=0x, count=%i%x\n",word,expected,got,totCount_);
         errCount_++;
         return(false);
      }
   }

   return(true);
}

