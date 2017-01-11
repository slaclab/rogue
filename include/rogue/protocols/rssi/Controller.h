/**
 *-----------------------------------------------------------------------------
 * Title      : RSSI Controller Class
 * ----------------------------------------------------------------------------
 * File       : Controller.h
 * Created    : 2017-01-07
 * Last update: 2017-01-07
 * ----------------------------------------------------------------------------
 * Description:
 * RSSI Controller
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
#ifndef __ROGUE_PROTOCOLS_RSSI_CONTROLLER_H__
#define __ROGUE_PROTOCOLS_RSSI_CONTROLLER_H__
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <boost/enable_shared_from_this.hpp>
#include <boost/python.hpp>
#include <stdint.h>

namespace rogue {
   namespace protocols {
      namespace rssi {

         class Application;
         class Transport;

         //! RSSI Controller Class
         class Controller : public boost::enable_shared_from_this<rogue::protocols::rssi::Controller> {

               static const uint8_t  Version       = 1;
               static const uint8_t  TimeoutUnit   = 6; // 1e-6
               static const uint8_t  LocMaxBuffers = 32;
               static const uint16_t LocMaxSegment = 8000;
               static const uint16_t ReqRetranTout = 60;
               static const uint16_t ReqAckTout    = 30;
               static const uint16_t ReqNullTout   = 300;
               static const uint8_t  ReqMaxRetran  = 4;
               static const uint8_t  ReqMaxCumAck  = 8;
               static const uint32_t ReqConnId     = 0x4321DEFA;
               static const uint32_t TryPeriod     = 1000000; // 1 second

               //! Connection states
               enum States : uint32_t { StClosed  = 0,
                                        StSendSyn = 1,
                                        StWaitSyn = 2,
                                        StSendAck = 3,
                                        StOpen    = 4,
                                        StSendRst = 5 };

               //! Int buffer size
               uint32_t intBuffSize_;

               //! Current state
               uint32_t state_;

               //! Last state update time
               struct timeval stTime_;

               //! Last packet rx time
               struct timeval rxTime_;

               //! Last packet tx time
               struct timeval txTime_;

               //! Transport module
               boost::shared_ptr<rogue::protocols::rssi::Transport> tran_;

               //! Application module
               boost::shared_ptr<rogue::protocols::rssi::Application> app_;

               boost::thread* thread_;

               //! mutex
               boost::mutex mtx_;

               //! Transmit frame helper
               void sendFrame(boost::shared_ptr<rogue::interfaces::stream::Frame> frame);

               //! Helper function to determine if time has elapsed
               bool timePassed ( struct timeval *currTime, struct timeval *lastTime, uint32_t usec );

               //! Thread background
               void runThread();

            public:

               //! Class creation
               static boost::shared_ptr<rogue::protocols::rssi::Controller> 
                  create ( boost::shared_ptr<rogue::protocols::rssi::Transport> tran,
                           boost::shared_ptr<rogue::protocols::rssi::Application> app );

               //! Setup class in python
               static void setup_python();

               //! Creator
               Controller( boost::shared_ptr<rogue::protocols::rssi::Transport> tran,
                           boost::shared_ptr<rogue::protocols::rssi::Application> app );

               //! Destructor
               ~Controller();

               //! Frame received at transport interface
               void transportRx( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );

               //! Frame received at application interface
               void applicationRx( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );

               //! Transport frame allocation request
               boost::shared_ptr<rogue::interfaces::stream::Frame>
                  reqFrame ( uint32_t size, uint32_t maxBuffSize );

         };

         // Convienence
         typedef boost::shared_ptr<rogue::protocols::rssi::Controller> ControllerPtr;

      }
   }
};

#endif

