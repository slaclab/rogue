/**
 *-----------------------------------------------------------------------------
 * Title      : RSSI Client Class
 * ----------------------------------------------------------------------------
 * Description:
 * UDP Client
 * ----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to
 * the license terms in the LICENSE.txt file found in the top-level directory
 * of this distribution and at:
 *    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
 * No part of the rogue software platform, including this file, may be
 * copied, modified, propagated, or distributed except according to the terms
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
**/
#ifndef __ROGUE_PROTOCOLS_RSSI_CLIENT_H__
#define __ROGUE_PROTOCOLS_RSSI_CLIENT_H__
#include <thread>
#include <stdint.h>

namespace rogue {
   namespace protocols {
      namespace rssi {

         class Transport;
         class Application;
         class Controller;

         //! RSSI Client Class
         class Client {

               //! Transport module
               std::shared_ptr<rogue::protocols::rssi::Transport> tran_;

               //! Application module
               std::shared_ptr<rogue::protocols::rssi::Application> app_;

               //! Client module
               std::shared_ptr<rogue::protocols::rssi::Controller> cntl_;

            public:

               //! Class creation
               static std::shared_ptr<rogue::protocols::rssi::Client> create (uint32_t segSize);

               //! Setup class in python
               static void setup_python();

               //! Creator
               Client(uint32_t segSize);

               //! Destructor
               ~Client();

               //! Get transport interface
               std::shared_ptr<rogue::protocols::rssi::Transport> transport();

               //! Application module
               std::shared_ptr<rogue::protocols::rssi::Application> application();

               //! Get state
               bool getOpen();

               //! Get Down Count
               uint32_t getDownCount();

               //! Get Drop Count
               uint32_t getDropCount();

               //! Get Retransmit Count
               uint32_t getRetranCount();

               //! Get locBusy
               bool getLocBusy();

               //! Get locBusyCnt
               uint32_t getLocBusyCnt();

               //! Get remBusy
               bool getRemBusy();

               //! Get remBusyCnt
               uint32_t getRemBusyCnt();

               void     setLocTryPeriod(uint32_t val);
               uint32_t getLocTryPeriod();

               void     setLocMaxBuffers(uint8_t val);
               uint8_t  getLocMaxBuffers();

               void     setLocMaxSegment(uint16_t val);
               uint16_t getLocMaxSegment();

               void     setLocCumAckTout(uint16_t val);
               uint16_t getLocCumAckTout();

               void     setLocRetranTout(uint16_t val);
               uint16_t getLocRetranTout();

               void     setLocNullTout(uint16_t val);
               uint16_t getLocNullTout();

               void     setLocMaxRetran(uint8_t val);
               uint8_t  getLocMaxRetran();

               void     setLocMaxCumAck(uint8_t val);
               uint8_t  getLocMaxCumAck();

               uint8_t  curMaxBuffers();
               uint16_t curMaxSegment();
               uint16_t curCumAckTout();
               uint16_t curRetranTout();
               uint16_t curNullTout();
               uint8_t  curMaxRetran();
               uint8_t  curMaxCumAck();

               //! Set timeout in microseconds for frame transmits
               void setTimeout(uint32_t timeout);

               //! Stop connection
               void stop();

               //! Start connection
               void start();

         };

         // Convenience
         typedef std::shared_ptr<rogue::protocols::rssi::Client> ClientPtr;

      }
   }
};

#endif

