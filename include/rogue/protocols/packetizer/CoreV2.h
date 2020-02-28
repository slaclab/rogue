/**
 *-----------------------------------------------------------------------------
 * Title      : Packetizer Core Class
 * ----------------------------------------------------------------------------
 * File       : CoreV2.h
 * Created    : 2018-02-02
 * ----------------------------------------------------------------------------
 * Description:
 * Packetizer Core, Version 2
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
#ifndef __ROGUE_PROTOCOLS_PACKETIZER_CORE_V2_H__
#define __ROGUE_PROTOCOLS_PACKETIZER_CORE_V2_H__
#include <thread>
#include <stdint.h>

namespace rogue {
   namespace protocols {
      namespace packetizer {

         class Transport;
         class Application;
         class ControllerV2;

         //! Core Class
         class CoreV2 {

               //! Transport module
               std::shared_ptr<rogue::protocols::packetizer::Transport> tran_;

               //! Application modules
               std::shared_ptr<rogue::protocols::packetizer::Application> app_[256];

               //! Core module
               std::shared_ptr<rogue::protocols::packetizer::ControllerV2> cntl_;

            public:

               //! Class creation
               static std::shared_ptr<rogue::protocols::packetizer::CoreV2> create (bool enIbCrc, bool enObCrc, bool enSsi);

               //! Setup class in python
               static void setup_python();

               //! Creator
               CoreV2(bool enIbCrc, bool enObCrc, bool enSsi);

               //! Destructor
               ~CoreV2();

               //! Get transport interface
               std::shared_ptr<rogue::protocols::packetizer::Transport> transport();

               //! Application module
               std::shared_ptr<rogue::protocols::packetizer::Application> application(uint8_t dest);

               //! Get drop count
               uint32_t getDropCount();

               //! Set timeout
               void setTimeout(uint32_t timeout);
         };

         // Convenience
         typedef std::shared_ptr<rogue::protocols::packetizer::CoreV2> CoreV2Ptr;

      }
   }
};

#endif

