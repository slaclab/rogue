/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Stream Interface Rate Drop
 * ----------------------------------------------------------------------------
 * File          : RateDrop.h
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 08/25/2020
 *-----------------------------------------------------------------------------
 * Description :
 *    Drops frames at a specified rate.
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
#ifndef __ROGUE_INTERFACES_STREAM_RATE_DROP_H__
#define __ROGUE_INTERFACES_STREAM_RATE_DROP_H__
#include <stdint.h>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/Logging.h>

namespace rogue {
   namespace interfaces {
      namespace stream {

         //! Stream Rate Drop
         /** Drops frames at a defined rate. The rate value will defined as either the number of frames to drop
          * between each kept frame or the time interval  between each kept frame. If the period flag is true the passed
          * value will be interpreted as the time between kept frames in seconds. If the rate flag is false the value will
          * be interpreted as the number of frames to drop between each ketp frame.
          */
         class RateDrop : public rogue::interfaces::stream::Master,
                          public rogue::interfaces::stream::Slave {

               // Configurations
               bool     periodFlag_;

               uint32_t dropTarget_;

               struct timeval timePeriod_;

               // Status
               uint32_t dropCount_;

               struct timeval nextPeriod_;

            public:

               //! Create a RateDrop object and return as a RateDropPtr
               /** @param period Set to true to define the parameter as a period value.
                * @param value Period value or drop count
                * @return RateDrop object as a RateDropPtr
                */
               static std::shared_ptr<rogue::interfaces::stream::RateDrop> create(bool period, double value);

               // Setup class for use in python
               static void setup_python();

               // Create a RateDrop object
               RateDrop(bool period, double value);

               // Destroy the RateDrop
               ~RateDrop();

               // Receive frame from Master
               void acceptFrame ( std::shared_ptr<rogue::interfaces::stream::Frame> frame );

         };

         //! Alias for using shared pointer as RateDropPtr
         typedef std::shared_ptr<rogue::interfaces::stream::RateDrop> RateDropPtr;
      }
   }
}
#endif

