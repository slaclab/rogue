/**
 *-----------------------------------------------------------------------------
 * Title      : RSSI Transport Class
 * ----------------------------------------------------------------------------
 * Description:
 * RSSI Transport
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
#ifndef __ROGUE_PROTOCOLS_RSSI_TRANSPORT_H__
#define __ROGUE_PROTOCOLS_RSSI_TRANSPORT_H__
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <stdint.h>
#include <rogue/Queue.h>

namespace rogue {
   namespace protocols {
      namespace rssi {

         class Controller;

         //! RSSI Transport Class
         class Transport : public rogue::interfaces::stream::Master,
                           public rogue::interfaces::stream::Slave {

               //! Core module
               std::shared_ptr<rogue::protocols::rssi::Controller> cntl_;

            public:

               //! Class creation
               static std::shared_ptr<rogue::protocols::rssi::Transport> create ();

               //! Setup class in python
               static void setup_python();

               //! Creator
               Transport();

               //! Destructor
               ~Transport();

               //! Setup links
               void setController ( std::shared_ptr<rogue::protocols::rssi::Controller> cntl );

               //! Accept a frame from master
               void acceptFrame ( std::shared_ptr<rogue::interfaces::stream::Frame> frame );
         };

         // Convienence
         typedef std::shared_ptr<rogue::protocols::rssi::Transport> TransportPtr;

      }
   }
};

#endif

