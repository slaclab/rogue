/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Stream Filter
 * ----------------------------------------------------------------------------
 * File          : Filter.h
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 11/01/2018
 *-----------------------------------------------------------------------------
 * Description :
 *    AXI Stream Filter
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
#ifndef __ROGUE_INTERFACES_STREAM_FILTER_H__
#define __ROGUE_INTERFACES_STREAM_FILTER_H__
#include <stdint.h>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/Logging.h>

namespace rogue {
   namespace interfaces {
      namespace stream {

         //! Stream Filter
         /** In some cases a Frame will have a non zero channel number. This can be the case
          * when reading data from a Data file using a StreamWReader object. This can also
          * occur when receiving data from a Batcher protocol Frame Splitter. The Filter allows
          * a Slave to be sure it only receives Frame data for a particular channel. The
          * Filter object has a configured channel number and a flag to determine if Frame
          * objects with a non-zero error field will be dropped.
          */
         class Filter : public rogue::interfaces::stream::Master,
                        public rogue::interfaces::stream::Slave {

               std::shared_ptr<rogue::Logging> log_;

               // Configurations
               bool     dropErrors_;
               uint8_t  channel_;

            public:

               //! Create a Filter object and return as a FilterPtr
               /** @param dropErrors Set to True to drop errored Frames
                * @param channel Set channel number to allow through the filter.
                * @return Filter object as a FilterPtr
                */
               static std::shared_ptr<rogue::interfaces::stream::Filter> create(bool dropErrors, uint8_t channel);

               // Setup class for use in python
               static void setup_python();

               // Create a Filter object
               Filter(bool dropErrors, uint8_t channel);

               // Destroy the Filter
               ~Filter();

               // Receive frame from Master
               void acceptFrame ( std::shared_ptr<rogue::interfaces::stream::Frame> frame );

         };

         //! Alias for using shared pointer as FilterPtr
         typedef std::shared_ptr<rogue::interfaces::stream::Filter> FilterPtr;
      }
   }
}
#endif

