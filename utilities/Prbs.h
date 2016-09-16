/**
 *-----------------------------------------------------------------------------
 * Title         : PRBS Receive And Transmit Class
 * ----------------------------------------------------------------------------
 * File          : Prbs.h
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
#ifndef __UTILITIES_PRBS_H__
#define __UTILITIES_PRBS_H__
#include <stdint.h>

namespace utilities {

   //! PRBS master / slave class
   /*
    * Engine can be used as either a master or slave. 
    * Internal thread can en enabled for auto frame generation
    */
   class Prbs : public interfaces::stream::Slave, public interfaces::stream::Master {
         uint32_t * _taps;
         uint32_t   _tapCnt;
         uint32_t   _width;
         uint32_t   _sequence;
         uint32_t   _tSize;

         uint32_t flfsr(uint32_t input);

         //! Thread background
         void runThread();

      public:

         //! Creator with width and variable taps
         Prbs(uint32_t width, uint32_t tapCnt, ... );

         //! Creator with default taps and size
         Prbs();

         //! Deconstructor
         ~Prbs();

         //! Generate a data frame
         void genFrame (uint32_t size);

         //! Auto run data generation
         void enable(uint32_t size);

         //! Disable auto generation
         void disable();

         //! Generate a buffer. Called from master
         boost::shared_ptr<interfaces::stream::Frame>
            acceptReq ( uint32_t size, bool zeroCopyEn);

         //! Accept a frame from master
         bool acceptFrame ( boost::shared_ptr<interfaces::stream::Frame> frame );

         //! Return a buffer
         void retBuffer(uint8_t * data, uint32_t meta, uint32_t rawSize);
   };
}

#endif


