/**
 *-----------------------------------------------------------------------------
 * Title         : PRBS Receive And Transmit Class
 * ----------------------------------------------------------------------------
 * File          : Prbs.h
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
#ifndef __ROGUE_UTILITIES_PRBS_H__
#define __ROGUE_UTILITIES_PRBS_H__
#include <stdint.h>
#include <boost/thread.hpp>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/stream/Master.h>

namespace rogue {
   namespace utilities {

      //! PRBS master / slave class
      /*
       * Engine can be used as either a master or slave. 
       * Internal thread can en enabled for auto frame generation
       */
      class Prbs : public rogue::interfaces::stream::Slave, public rogue::interfaces::stream::Master {

            //! PRBS taps
            uint32_t * taps_;

            //! PRBS tap count
            uint32_t   tapCnt_;

            //! Data width in bytes
            uint32_t   width_;

            //! Data width in bytes
            uint32_t   byteWidth_;

            //! Min size
            uint32_t   minSize_;

            //! RX Count
            boost::mutex rxMtx_;

            //! rx sequence tracking
            uint32_t   rxSeq_;

            //! RX Error count
            uint32_t   rxErrCount_;

            //! Rx count
            uint32_t   rxCount_;

            //! Rx bytes
            uint32_t   rxBytes_;

            //! TX Mutex
            boost::mutex txMtx_;

            //! tx sequence tracking
            uint32_t   txSeq_;

            //! Transmit size
            uint32_t   txSize_;

            //! TX Error count
            uint32_t   txErrCount_;

            //! TX count
            uint32_t   txCount_;

            //! TX bytes
            uint32_t   txBytes_;

            //! Logger
            rogue::Logging *rxLog_;
            rogue::Logging *txLog_;

            //! TX thread
            boost::thread* txThread_;

            //! Internal computation 
            uint32_t flfsr(uint32_t input);

            //! Thread background
            void runThread();

            //! Init state
            void init(uint32_t width, uint32_t tapCnt);

            //! Read data with the appropriate width and set passed 32-bit integer pointer
            uint32_t readSingle ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame, 
                                  uint32_t offset, uint32_t * value );

            //! Write data with the appropriate width
            uint32_t writeSingle ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame, 
                                   uint32_t offset, uint32_t value );

         public:

            //! Class creation
            static boost::shared_ptr<rogue::utilities::Prbs> create ();

            //! Setup class in python
            static void setup_python();

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

            //! Get rx errors
            uint32_t getRxErrors();

            //! Get rx count
            uint32_t getRxCount();

            //! Get rx total bytes
            uint32_t getRxBytes();

            //! Get tx errors
            uint32_t getTxErrors();

            //! Get tx count
            uint32_t getTxCount();

            //! Get tx total bytes
            uint32_t getTxBytes();

            //! Reset counters
            void resetCount();

            //! Accept a frame from master
            void acceptFrame ( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );
      };

      // Convienence
      typedef boost::shared_ptr<rogue::utilities::Prbs> PrbsPtr;
   }
}
#endif

