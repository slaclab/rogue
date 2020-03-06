/**
 *-----------------------------------------------------------------------------
 * Title      : Packetizer Controller V2 Class
 * ----------------------------------------------------------------------------
 * File       : ControllerV2.h
 * Created    : 2018-02-02
 * ----------------------------------------------------------------------------
 * Description:
 * Packetizer Controller, Version 2
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
#ifndef __ROGUE_PROTOCOLS_PACKETIZER_CONTROLLER_V2_H__
#define __ROGUE_PROTOCOLS_PACKETIZER_CONTROLLER_V2_H__
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
         class ControllerV2 : public Controller, public rogue::EnableSharedFromThis<rogue::protocols::packetizer::ControllerV2> {

               bool     enIbCrc_;
               bool     enObCrc_;

            public:

               //! Class creation
               static std::shared_ptr<rogue::protocols::packetizer::ControllerV2>
                  create ( bool enIbCrc, bool enObCrc, bool enSsi,
                           std::shared_ptr<rogue::protocols::packetizer::Transport> tran,
                           std::shared_ptr<rogue::protocols::packetizer::Application> * app );

               //! Creator
               ControllerV2( bool enIbCrc, bool enObCrc, bool enSsi,
                           std::shared_ptr<rogue::protocols::packetizer::Transport> tran,
                           std::shared_ptr<rogue::protocols::packetizer::Application> * app );

               //! Destructor
               ~ControllerV2();

               //! Frame received at transport interface
               void transportRx( std::shared_ptr<rogue::interfaces::stream::Frame> frame );

               //! Frame received at application interface
               void applicationRx( std::shared_ptr<rogue::interfaces::stream::Frame> frame, uint8_t id);
         };

         // Convenience
         typedef std::shared_ptr<rogue::protocols::packetizer::ControllerV2> ControllerV2Ptr;

      }
   }
};

#endif

