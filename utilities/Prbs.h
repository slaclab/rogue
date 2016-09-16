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
#include <boost/thread.hpp>

namespace utilities {

   //! PRBS master / slave class
   /*
    * Engine can be used as either a master or slave. 
    * Internal thread can en enabled for auto frame generation
    */
   class Prbs : public interfaces::stream::Slave, public interfaces::stream::Master {
         uint32_t * taps_;
         uint32_t   tapCnt_;
         uint32_t   width_;
         uint32_t   sequence_;
         uint32_t   txSize_;
         uint32_t   errCount_;
         uint32_t   totCount_;
         uint32_t   totBytes_;
         bool       enMessages_;

         boost::thread* thread_;

         //! Internal computation 
         uint32_t flfsr(uint32_t input);

         //! Thread background
         void runThread();

         //! Reset state
         void init(uint32_t width, uint32_t tapCnt);

      public:

         //! Class creation
         static boost::shared_ptr<utilities::Prbs> create ();

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

         //! Get errors
         uint32_t getErrors();

         //! Get rx/tx count
         uint32_t getCount();

         //! Get total bytes
         uint32_t getBytes();

         //! Reset counters
         void resetCount();

         //! Enable messages
         void enMessages(bool state);

         //! Accept a frame from master
         bool acceptFrame ( boost::shared_ptr<interfaces::stream::Frame> frame );
   };

   // Convienence
   typedef boost::shared_ptr<utilities::Prbs> PrbsPtr;
}

#endif


