/**
 *-----------------------------------------------------------------------------
 * Title      : UDP Common Functions
 * ----------------------------------------------------------------------------
 * Description:
 * UDP Common
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
#ifndef __ROGUE_PROTOCOLS_UDP_CORE_H__
#define __ROGUE_PROTOCOLS_UDP_CORE_H__
#include <rogue/Logging.h>
#include <stdint.h>
#include <netdb.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/ip.h>

namespace rogue {
   namespace protocols {
      namespace udp {

         const uint32_t MaxJumboPayload = 8900;
         const uint32_t MaxStdPayload   = 1400;

         const uint32_t JumboMTU = 9000;
         const uint32_t StdMTU   = 1500;

         //! UDP Core
         class Core {

            protected:

               std::shared_ptr<rogue::Logging> udpLog_;

               //! Jumbo frames enables
               bool jumbo_;

               //! Socket
               int32_t  fd_;

               //! Remote socket address
               struct sockaddr_in remAddr_;

               //! Timeout value
               struct timeval timeout_;

               std::thread* thread_;
               bool threadEn_;

               //! mutex
               std::mutex udpMtx_;

            public:

               //! Setup class in python
               static void setup_python();

               //! Creator
               Core(bool jumbo);

               //! Destructor
               ~Core();

               //! Stop the interface
               void stop();

               //! Return max payload
               uint32_t maxPayload();

               //! Set number of expected incoming buffers
               bool setRxBufferCount(uint32_t count);

               //! Set timeout for frame transmits in microseconds
               void setTimeout(uint32_t timeout);
         };

         // Convenience
         typedef std::shared_ptr<rogue::protocols::udp::Core> CorePtr;
      }
   }
};

#endif

