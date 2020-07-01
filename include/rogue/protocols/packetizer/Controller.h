/**
 *-----------------------------------------------------------------------------
 * Title      : Packetizer Controller Class
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
#include <memory>
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
               bool     enSsi_;
               uint32_t appIndex_;
               uint32_t tranIndex_;
               bool     transSof_[256];
               uint32_t tranCount_[256];
               uint32_t crc_[256];
               uint8_t  tranDest_;
               uint32_t dropCount_;
               uint32_t headSize_;
               uint32_t tailSize_;
               uint32_t alignSize_;

               struct timeval timeout_;

               std::shared_ptr<rogue::Logging> log_;

               std::shared_ptr<rogue::interfaces::stream::Frame> tranFrame_[256];

               std::mutex appMtx_;
               std::mutex tranMtx_;

               std::shared_ptr<rogue::protocols::packetizer::Transport> tran_;
               std::shared_ptr<rogue::protocols::packetizer::Application> * app_;

               rogue::Queue<std::shared_ptr<rogue::interfaces::stream::Frame>> tranQueue_;

            public:

               //! Creator
               Controller( std::shared_ptr<rogue::protocols::packetizer::Transport> tran,
                           std::shared_ptr<rogue::protocols::packetizer::Application> * app,
                           uint32_t headSize, uint32_t tailSize, uint32_t alignSize, bool enSsi );

               //! Destructor
               ~Controller();

               //! Transport frame allocation request
               std::shared_ptr<rogue::interfaces::stream::Frame> reqFrame ( uint32_t size);

               //! Frame received at transport interface
               virtual void transportRx( std::shared_ptr<rogue::interfaces::stream::Frame> frame );

               //! Stop transmit queue
               void stopQueue();

               //! Stop
               void stop();

               //! Interface for transport transmitter thread
               std::shared_ptr<rogue::interfaces::stream::Frame> transportTx ();

               //! Frame received at application interface
               virtual void applicationRx( std::shared_ptr<rogue::interfaces::stream::Frame> frame, uint8_t id);

               //! Get drop count
               uint32_t getDropCount();

               //! Set timeout in microseconds for frame transmits
               void setTimeout(uint32_t timeout);
         };

         // Convenience
         typedef std::shared_ptr<rogue::protocols::packetizer::Controller> ControllerPtr;

      }
   }
};

#endif

