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
#include <rogue/Queue.h>
#include <rogue/Logging.h>

namespace rogue {
   namespace protocols {
      namespace packetizer {

         class Application;
         class Transport;
         class Header;

         //! Packetizer Controller Class
         class Controller {

            protected:

               // parameters
               uint32_t appIndex_;
               uint32_t tranIndex_;
               bool     transSof_[256];
               uint32_t tranCount_[256];
               uint32_t crcInit_[256];
               uint8_t  tranDest_;
               uint32_t dropCount_;
               uint32_t timeout_;
               uint32_t headSize_;
               uint32_t tailSize_;
               uint32_t alignSize_;

               rogue::LoggingPtr log_;

               boost::shared_ptr<rogue::interfaces::stream::Frame> tranFrame_[256];

               boost::mutex appMtx_;
               boost::mutex tranMtx_;

               boost::shared_ptr<rogue::protocols::packetizer::Transport> tran_;
               boost::shared_ptr<rogue::protocols::packetizer::Application> * app_;

               rogue::Queue<boost::shared_ptr<rogue::interfaces::stream::Frame>> tranQueue_;

            public:

               //! Setup class in python
               static void setup_python();

               //! Creator
               Controller( boost::shared_ptr<rogue::protocols::packetizer::Transport> tran,
                           boost::shared_ptr<rogue::protocols::packetizer::Application> * app,
                           uint32_t headSize, uint32_t tailSize, uint32_t alignSize );

               //! Destructor
               ~Controller();

               //! Transport frame allocation request
               boost::shared_ptr<rogue::interfaces::stream::Frame> reqFrame ( uint32_t size);

               //! Frame received at transport interface
               virtual void transportRx( boost::shared_ptr<rogue::interfaces::stream::Frame> frame );

               //! Interface for transport transmitter thread
               boost::shared_ptr<rogue::interfaces::stream::Frame> transportTx ();

               //! Frame received at application interface
               virtual void applicationRx( boost::shared_ptr<rogue::interfaces::stream::Frame> frame, uint8_t id);

               //! Get drop count
               uint32_t getDropCount();

               //! Set timeout in microseconds for frame transmits
               void setTimeout(uint32_t timeout);
         };

         // Convienence
         typedef boost::shared_ptr<rogue::protocols::packetizer::Controller> ControllerPtr;

      }
   }
};

#endif

