/**
 *-----------------------------------------------------------------------------
 * Title         : PRBS Receive And Transmit Class
 * ----------------------------------------------------------------------------
 * File          : Prbs.cpp
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 08/11/2014
 * Last update   : 08/11/2014
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

namespace is = interfaces::stream;
namespace ut = utilities;

//! Creator with width and variable taps
ut::Prbs::Prbs(uint32_t width, uint32_t tapCnt, ... ) {
   va_list a_list;
   uint32_t   x;

   _sequence = 0;
   _width    = width;
   _tapCnt   = tapCnt;

   _taps = (uint32_t *)malloc(sizeof(uint32_t)*_tapCnt);

   va_start(a_list,tapCnt);
   for(x=0; x < tapCnt; x++) _taps[x] = va_arg(a_list,uint32_t);
   va_end(a_list);
}

//! Creator with default taps and size
ut::Prbs::Prbs() {
   _sequence = 0;
   _width    = 32;
   _tapCnt   = 4;

   _taps = (uint32_t *)malloc(sizeof(uint32_t)*_tapCnt);

   _taps[0] = 1;
   _taps[1] = 2;
   _taps[2] = 6;
   _taps[3] = 31;
}

//! Deconstructor
ut::Prbs::~Prbs() {
   free(_taps);
}

uint32_t ut::Prbs::flfsr(uint32_t input) {
   uint32_t bit = 0;
   uint32_t x;

   for (x=0; x < _tapCnt; x++) bit = bit ^ (input >> _taps[x]);

   bit = bit & 1;

   return ((input << 1) | bit);
}

//! Auto run data generation
void ut::Prbs::enable(uint32_t size) {
   //_tSize = size;

   //boost::thread t{runThread};
}

//! Disable auto generation
void ut::Prbs::disable() {


}

//! Generate a buffer. Called from master
is::FramePtr ut::Prbs::acceptReq ( uint32_t size, bool zeroCopyEn) {
   is::FramePtr ret;
   is::BufferPtr buff;
   uint8_t * data;

   if ( (data = (uint8_t *)malloc(size)) == NULL ) return(ret);

   buff = is::Buffer::create(getSlave(),data,0,size);
   ret  = is::Frame::create(zeroCopyEn);

   ret->appendBuffer(buff);
   return(ret);
}

//! Return a buffer
void ut::Prbs::retBuffer(uint8_t * data, uint32_t meta, uint32_t rawSize) {
   printf("Deleteing prbs buffer\n");
   free(data);
}

//! Generate a data frame
void ut::Prbs::genFrame (uint32_t size) {
   uint32_t   word;
   uint32_t   value;
   uint32_t   data32[2];
   uint16_t * data16;

   is::FramePtr fr = reqFrame(size,true);

   data16 = (uint16_t *)data32;
   value = _sequence;

   if ( _width == 16 ) {
      if ((( size % 2 ) != 0) || size < 6 ) return;
      data16[0] = _sequence & 0xFFFF;
      data16[1] = (size - 2) / 2;
      fr->write(data16,0,4);
   }
   else if ( _width == 32 ) {
      if ((( size % 4 ) != 0) || size < 12 ) return;
      data32[0] = _sequence;
      data32[1] = (size - 4) / 4;
      fr->write(data32,0,8);
   }
   else {
      fprintf(stderr,"Bad gen width = %i\n",_width);
      return;
   }

   for (word = 2; word < size/(_width/8); word++) {
      value = flfsr(value);
      if      ( _width == 16 ) fr->write(&value,2,word*2);
      else if ( _width == 32 ) fr->write(&value,4,word*4);
   }

   if      ( _width == 16 ) _sequence = data16[0] + 1;
   else if ( _width == 32 ) _sequence = data32[0] + 1;

   sendFrame(fr);
}

//! Accept a frame from master
bool ut::Prbs::acceptFrame ( is::FramePtr frame ) {
   uint32_t   eventLength;
   uint32_t   expected;
   uint32_t   got;
   uint32_t   word;
   uint32_t   min;
   uint32_t   data32[2];
   uint16_t * data16;
   uint32_t   size;

   data16 = (uint16_t *)data32;

   size = frame->getPayload();

   if ( _width == 16 ) {
      frame->read(data16,0,4);
      expected    = data16[0];
      eventLength = (data16[1] * 2) + 2;
      min         = 6;
   }
   else if ( _width == 32 ) {
      frame->read(data16,0,8);
      expected    = data32[0];
      eventLength = (data32[1] * 4) + 4;
      min         = 12;
   }
   else {
      fprintf(stderr,"Bad process width = %i\n",_width);
      return(false);
   }

   if (size < min || eventLength != size) {
      fprintf(stderr,"Bad size. exp=%i, min=%i, got=%i\n",eventLength,min,size);
      return(false);
   }

   if ( _sequence != 0 && _sequence != expected ) {
      fprintf(stderr,"Bad Sequence. exp=%i, got=%i\n",_sequence,expected);
      _sequence = expected + 1;
      return(false);
   }
   _sequence = expected + 1;

   for (word = 2; word < size/(_width/8); word++) {
      expected = flfsr(expected);

      if      ( _width == 16 ) frame->read(&got,word*2,2);
      else if ( _width == 32 ) frame->read(&got,word*4,4);
      else got = 0;

      if (expected != got) {
         fprintf(stderr,"Bad value at index %i. exp=0x%x, got=0x%x\n",word,expected,got);
         return(false);
      }
   }
   return(true);
}

