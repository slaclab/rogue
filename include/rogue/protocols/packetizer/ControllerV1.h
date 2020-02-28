/**
 *-----------------------------------------------------------------------------
 * Title      : Packetizer Controller V1 Class
 * ----------------------------------------------------------------------------
 * File       : ControllerV1.h
 * Created    : 2018-02-02
 * ----------------------------------------------------------------------------
 * Description:
 * Packetizer Controller, Version 1
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
#ifndef __ROGUE_PROTOCOLS_PACKETIZER_CONTROLLER_V1_H__
#define __ROGUE_PROTOCOLS_PACKETIZER_CONTROLLER_V1_H__
#include <rogue/protocols/packetizer/Controller.h>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <memory>
#include <stdint.h>
#include <rogue/Queue.h>
#include <rogue/Logging.h>
#include <rogue/EnableSharedFromThis.h>

namespace rogue {
   namespace protocols {
      namespace packetizer {

         class Application;
         class Transport;
         class Header;


         //! Packetizer Controller Class
         class ControllerV1 : public Controller, public rogue::EnableSharedFromThis<rogue::protocols::packetizer::ControllerV1> {

            public:

               //! Class creation
               static std::shared_ptr<rogue::protocols::packetizer::ControllerV1>
                  create ( bool enSsi,
                           std::shared_ptr<rogue::protocols::packetizer::Transport> tran,
                           std::shared_ptr<rogue::protocols::packetizer::Application> * app );

               //! Creator
               ControllerV1( bool enSsi,
                             std::shared_ptr<rogue::protocols::packetizer::Transport> tran,
                             std::shared_ptr<rogue::protocols::packetizer::Application> * app );

               //! Destructor
               ~ControllerV1();

               //! Frame received at transport interface
               void transportRx( std::shared_ptr<rogue::interfaces::stream::Frame> frame );

               //! Frame received at application interface
               void applicationRx( std::shared_ptr<rogue::interfaces::stream::Frame> frame, uint8_t id);
         };

         // Convenience
         typedef std::shared_ptr<rogue::protocols::packetizer::ControllerV1> ControllerV1Ptr;

      }
   }
};

#endif

