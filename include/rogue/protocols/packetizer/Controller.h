/**
 *-----------------------------------------------------------------------------
 * Title      : Packetizer Controller Class
 * ----------------------------------------------------------------------------
 * File       : Controller.h
 * Created    : 2017-01-07
 * Last update: 2017-01-07
 * ----------------------------------------------------------------------------
 * Description:
 * Packetizer Controller
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
#ifndef __ROGUE_PROTOCOLS_PACKETIZER_CONTROLLER_H__
#define __ROGUE_PROTOCOLS_PACKETIZER_CONTROLLER_H__
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <boost/enable_shared_from_this.hpp>
#include <boost/python.hpp>
#include <stdint.h>
#include <queue>

namespace rogue {
   namespace protocols {
      namespace packetizer {

         class Application;
         class Transport;
         class Header;

         //! Packetizer Controller Class
         class Controller : public boost::enable_shared_from_this<rogue::protocols::packetizer::Controller> {

               //static const uint8_t  Version       = 1;
               //static const uint8_t  TimeoutUnit   = 3; // 1e-3

               // Connection parameters
               //uint32_t locConnId_;
               //uint8_t  remMaxBuffers_;
               //uint16_t remMaxSegment_;

               //boost::thread* thread_;
               //boost::mutex   mtx_;

               //boost::condition_variable stCond_;
               //boost::condition_variable appCond_;

               boost::shared_ptr<rogue::protocols::packetizer::Transport> tran_;
               boost::shared_ptr<rogue::protocols::packetizer::Application> app_;

            public:

               //! Class creation
               static boost::shared_ptr<rogue::protocols::packetizer::Controller> 
                  create ( boost::shared_ptr<rogue::protocols::packetizer::Transport> tran,
                           boost::shared_ptr<rogue::protocols::packetizer::Application> app );

               //! Setup class in python
               static void setup_python();

               //! Creator
               Controller( boost::shared_ptr<rogue::protocols::packetizer::Transport> tran,
                           boost::shared_ptr<rogue::protocols::packetizer::Application> app );

               //! Destructor
               ~Controller();

               //! Transport frame allocation request
               boost::shared_ptr<rogue::interfaces::stream::Frame>
                  reqFrame ( uint32_t size, uint32_t maxBuffSize );

               //! Frame received at transport interface
               void transportRx( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );

               //! Frame received at application interface
               void applicationRx( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );

         };

         // Convienence
         typedef boost::shared_ptr<rogue::protocols::packetizer::Controller> ControllerPtr;

      }
   }
};

#endif

