/**
 *-----------------------------------------------------------------------------
 * Title         : PRBS Receive And Transmit Class
 * ----------------------------------------------------------------------------
 * File          : PrbsData.h
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
#ifndef __PRBS_DATA_H__
#define __PRBS_DATA_H__
#include <stdint.h>

// Main Class
class PrbsData {

      uint32_t * _taps;
      uint32_t   _tapCnt;
      uint32_t   _width;
      uint32_t   _sequence;

      uint32_t flfsr(uint32_t input);

   public:

      PrbsData(uint32_t width, uint32_t tapCnt, ... );
      PrbsData();
      ~PrbsData();

      void genData ( const void *data, uint32_t size );

      bool processData ( const void *data, uint32_t size );

};

#endif


