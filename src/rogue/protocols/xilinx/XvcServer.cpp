//-----------------------------------------------------------------------------
// Title      : JTAG Support
//-----------------------------------------------------------------------------
// Company    : SLAC National Accelerator Laboratory
//-----------------------------------------------------------------------------
// Description:
//-----------------------------------------------------------------------------
// This file is part of 'SLAC Firmware Standard Library'.
// It is subject to the license terms in the LICENSE.txt file found in the
// top-level directory of this distribution and at:
//    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
// No part of 'SLAC Firmware Standard Library', including this file,
// may be copied, modified, propagated, or distributed except according to
// the terms contained in the LICENSE.txt file.
//-----------------------------------------------------------------------------

#include <rogue/protocols/xilinx/XvcServer.h>
#include <rogue/protocols/xilinx/XvcConnection.h>

#include <sys/socket.h>
#include <sys/select.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <dlfcn.h>
#include <pthread.h>
#include <math.h>
#include <string>

namespace rpx = rogue::protocols::xilinx;

rpx::XvcServer::XvcServer(
                           uint16_t    port,
                           JtagDriver* drv,
                           unsigned    maxMsgSize
                         )
   : drv_        (drv       ),
     maxMsgSize_ (maxMsgSize)
{
   struct sockaddr_in a;
   int yes = 1;

   a.sin_family      = AF_INET;
   a.sin_addr.s_addr = INADDR_ANY;
   a.sin_port        = htons(port);

   if ((sd_ = ::socket(AF_INET, SOCK_STREAM, 0)) < 0)
      throw(rogue::GeneralError::create("XvcServer::XvcServer()", "Failed to create socket"));

   if (::setsockopt(sd_, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes)))
      throw(rogue::GeneralError::create("XvcServer::XvcServer()", "setsockopt(SO_REUSEADDR) failed"));

   if (::bind(sd_, (struct sockaddr *)&a, sizeof(a)))
      throw(rogue::GeneralError::create("XvcServer::XvcServer()", "Unable to bind Stream socket to local address"));

   if (::listen(sd_, 1))
      throw(rogue::GeneralError::create("XvcServer::XvcServer()", "Unable to listen on socket"));
}

void rpx::XvcServer::run(bool &threadEn, rogue::LoggingPtr log)
{

   fd_set rset;
   int maxFd;
   int nready;
   struct timeval timeout;

   while(threadEn) {

      FD_ZERO(&rset);
      FD_SET(sd_, &rset);

      // 1 Second Timeout
      timeout.tv_sec = 1;
      timeout.tv_usec = 0;

      nready = ::select(sd_+1, &rset, NULL, NULL, &timeout);

      if ( nready > 0 && FD_ISSET(sd_, &rset)) {
         try {
            XvcConnection conn(sd_, drv_, maxMsgSize_);
            conn.run();
         }
         catch (rogue::GeneralError &e)
         {
            log->debug("Sub-connection failed");
         }
      }
   }
}
