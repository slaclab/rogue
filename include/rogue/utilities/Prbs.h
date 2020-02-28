/**
 *-----------------------------------------------------------------------------
 * Title         : PRBS Receive And Transmit Class
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
#include <thread>
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

            //! Max size
            const static uint32_t MaxBytes = 64;

            //! PRBS taps
            uint8_t  * taps_;

            //! PRBS tap count
            uint32_t   tapCnt_;

            //! Data width in bytes
            uint32_t   width_;

            //! Data width in bytes
            uint32_t   byteWidth_;

            //! Min size
            uint32_t   minSize_;

            //! Lock
            std::mutex pMtx_;

            //! rx sequence tracking
            uint32_t   rxSeq_;

            //! RX Error count
            uint32_t   rxErrCount_;

            //! Rx count
            uint32_t   rxCount_;

            //! Rx bytes
            uint32_t   rxBytes_;

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

            //! Check payload
            bool       checkPl_;

            //! Gen payload
            bool       genPl_;

            //! Send count
            bool       sendCount_;

            //! Receive enable
            bool       rxEnable_;

            // Stats
            uint32_t lastRxCount_;
            uint32_t lastRxBytes_;
            struct timeval lastRxTime_;
            double   rxRate_;
            double   rxBw_;

            uint32_t lastTxCount_;
            uint32_t lastTxBytes_;
            struct timeval lastTxTime_;
            double   txRate_;
            double   txBw_;

            //! Logger
            std::shared_ptr<rogue::Logging> rxLog_;
            std::shared_ptr<rogue::Logging> txLog_;

            //! TX thread
            std::thread* txThread_;
            bool threadEn_;

            //! Internal computation
            void flfsr(uint8_t * data);

            //! Thread background
            void runThread();

            static double updateTime ( struct timeval *last );

         public:

            //! Class creation
            static std::shared_ptr<rogue::utilities::Prbs> create ();

            //! Setup class in python
            static void setup_python();

            //! Creator with default taps and size
            Prbs();

            //! Deconstructor
            ~Prbs();

            //! Set width
            void setWidth(uint32_t width);

            //! Set taps
            void setTaps(uint32_t tapCnt, uint8_t * taps);

#ifndef NO_PYTHON
            //! Set taps, python
            void setTapsPy(boost::python::object p);
#endif

            //! Send counter value
            void sendCount(bool state);

            //! Generate a data frame
            void genFrame (uint32_t size);

            //! Auto run data generation
            void enable(uint32_t size);

            //! Disable auto generation
            void disable();

            //! Get rx enable
            bool getRxEnable();

            //! Set rx enable
            void setRxEnable(bool);

            //! Get rx errors
            uint32_t getRxErrors();

            //! Get rx count
            uint32_t getRxCount();

            //! Get rx total bytes
            uint32_t getRxBytes();

            //! Get rx rate
            double getRxRate();

            //! Get rx bw
            double getRxBw();

            //! Get tx rate
            double getTxRate();

            //! Get tx bw
            double getTxBw();

            //! Get tx errors
            uint32_t getTxErrors();

            //! Get tx count
            uint32_t getTxCount();

            //! Get tx total bytes
            uint32_t getTxBytes();

            //! Set check payload flag, default = true
            void checkPayload(bool state);

            //! Set check generate flag, default = true
            void genPayload(bool state);

            //! Reset counters
            void resetCount();

            //! Accept a frame from master
            void acceptFrame ( std::shared_ptr<rogue::interfaces::stream::Frame> frame );
      };

      // Convenience
      typedef std::shared_ptr<rogue::utilities::Prbs> PrbsPtr;

   }
}
#endif

