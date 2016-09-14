/**
 *-----------------------------------------------------------------------------
 * Title         : PRBS Receive And Transmit Class
 * ----------------------------------------------------------------------------
 * File          : PrbsData.cpp
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 08/11/2014
 * Last update   : 08/11/2014
 *-----------------------------------------------------------------------------
 * Description :
 *    Class used to generate and receive PRBS test data.
 *-----------------------------------------------------------------------------
 * This file is part of the PGP card driver. It is subject to 
 * the license terms in the LICENSE.txt file found in the top-level directory 
 * of this distribution and at: 
    * https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
 * No part of the PGP card driver, including this file, may be 
 * copied, modified, propagated, or distributed except according to the terms 
 * contained in the LICENSE.txt file.
 *-----------------------------------------------------------------------------
**/
#include <PrbsData.h>
#include <stdarg.h>
#include <stdlib.h>
#include <stdio.h>

PrbsData::PrbsData (uint32_t width, uint32_t tapCnt, ...) {
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

PrbsData::PrbsData () {
   _sequence = 0;
   _width    = 32;
   _tapCnt   = 4;

   _taps = (uint32_t *)malloc(sizeof(uint32_t)*_tapCnt);

   _taps[0] = 1;
   _taps[1] = 2;
   _taps[2] = 6;
   _taps[3] = 31;
}

PrbsData::~PrbsData() {
   free(_taps);
}

void PrbsData::genData ( const void *data, uint32_t size ) {
   uint32_t   word;
   uint32_t   value;
   uint32_t * data32;
   uint16_t * data16;

   data32 = (uint32_t *)data;
   data16 = (uint16_t *)data;

   value = _sequence;

   if ( _width == 16 ) {
      if ((( size % 2 ) != 0) || size < 6 ) return;
      data16[0] = _sequence & 0xFFFF;
      data16[1] = (size - 2) / 2;
   }
   else if ( _width == 32 ) {
      if ((( size % 4 ) != 0) || size < 12 ) return;
      data32[0] = _sequence;
      data32[1] = (size - 4) / 4;
   }
   else {
      fprintf(stderr,"Bad gen width = %i\n",_width);
      return;
   }

   for (word = 2; word < size/(_width/8); word++) {
      value = flfsr(value);
      if      ( _width == 16 ) data16[word] = value;
      else if ( _width == 32 ) data32[word] = value;
   }

   if      ( _width == 16 ) _sequence = data16[0] + 1;
   else if ( _width == 32 ) _sequence = data32[0] + 1;
}

bool PrbsData::processData ( const void *data, uint32_t size ) {
   uint32_t   eventLength;
   uint32_t   expected;
   uint32_t   got;
   uint32_t   word;
   uint32_t   min;
   uint32_t * data32;
   uint16_t * data16;

   data32 = (uint32_t *)data;
   data16 = (uint16_t *)data;

   if ( _width == 16 ) {
      expected    = data16[0];
      eventLength = (data16[1] * 2) + 2;
      min         = 6;
   }
   else if ( _width == 32 ) {
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

      if      ( _width == 16 ) got = data16[word];
      else if ( _width == 32 ) got = data32[word];
      else got = 0;

      if (expected != got) {
         fprintf(stderr,"Bad value at index %i. exp=0x%x, got=0x%x\n",word,expected,got);
         return(false);
      }
   }
   return(true);
}

uint32_t PrbsData::flfsr(uint32_t input) {
   uint32_t bit = 0;
   uint32_t x;

   for (x=0; x < _tapCnt; x++) bit = bit ^ (input >> _taps[x]);

   bit = bit & 1;

   //return (input >> 1) | (bit << _width);
   return ((input << 1) | bit);
}

