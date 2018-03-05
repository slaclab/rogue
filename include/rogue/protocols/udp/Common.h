/**
 *-----------------------------------------------------------------------------
 * Title      : UDP Common Functions
 * ----------------------------------------------------------------------------
 * File       : Common.h
 * Created    : 2017-01-07
 * Last update: 2017-01-07
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
#ifndef __ROGUE_PROTOCOLS_UDP_COMMON_H__
#define __ROGUE_PROTOCOLS_UDP_COMMON_H__
#include <rogue/Logging.h>
#include <stdint.h>
#include <netdb.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/ip.h>

namespace rogue {
   namespace protocols {
      namespace udp {

         // Return payload size depending on jumbo mod
         inline uint32_t const & maxPayload ( bool jumbo ) {
            if ( jumbo ) return (8900);
            else return(1400);
         }

         //! Set UDP RX Size
         inline bool const & setRxSize(uint32_t size, rogue::Logging * log) {
            uint32_t   rwin;
            socklen_t  rwin_size=4;

            setsockopt(fd_, SOL_SOCKET, SO_RCVBUF, (char*)&size, sizeof(size));
            getsockopt(fd_, SOL_SOCKET, SO_RCVBUF, &rwin, &rwin_size);
            if(size > rwin) {
               log->critical("Error setting rx buffer size.");
               log->critical("Wanted %i got %i",size,rwin);
               log->critical("sudo sysctl -w net.core.rmem_max=size to increase in kernel");
               return(false);
            }
            return(true);
         }
      }
   }
};

#endif

