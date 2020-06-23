/**
 *-----------------------------------------------------------------------------
 * Title      : UDP Client Class
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
#ifndef __ROGUE_PROTOCOLS_UDP_CLIENT_H__
#define __ROGUE_PROTOCOLS_UDP_CLIENT_H__
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/Logging.h>
#include <thread>
#include <stdint.h>
#include <netdb.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/ip.h>

namespace rogue {
   namespace protocols {
      namespace udp {

         class Client : public rogue::protocols::udp::Core,
                        public rogue::interfaces::stream::Master,
                        public rogue::interfaces::stream::Slave {

               //! Address, hostname or ip address
               std::string address_;

               //! Remote port number
               uint16_t port_;

               //! Thread background
               void runThread();

            public:

               //! Class creation
               static std::shared_ptr<rogue::protocols::udp::Client>
                  create (std::string host, uint16_t port, bool jumbo);

               //! Setup class in python
               static void setup_python();

               //! Creator
               Client(std::string host, uint16_t port, bool jumbo);

               //! Destructor
               ~Client();

               //! Stop the interface
               void stop();

               //! Accept a frame from master
               void acceptFrame ( std::shared_ptr<rogue::interfaces::stream::Frame> frame );
         };

         // Convenience
         typedef std::shared_ptr<rogue::protocols::udp::Client> ClientPtr;

      }
   }
};

#endif

