//-----------------------------------------------------------------------------
// Title      : JTAG Support
//-----------------------------------------------------------------------------
// Company    : SLAC National Accelerator Laboratory
//-----------------------------------------------------------------------------
// Description: XvcServer.h
//-----------------------------------------------------------------------------
// This file is part of 'SLAC Firmware Standard Library'.
// It is subject to the license terms in the LICENSE.txt file found in the
// top-level directory of this distribution and at:
//    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
// No part of 'SLAC Firmware Standard Library', including this file,
// may be copied, modified, propagated, or distributed except according to
// the terms contained in the LICENSE.txt file.
//-----------------------------------------------------------------------------

#ifndef __ROGUE_PROTOCOLS_XILINX_XVC_SERVER_H__
#define __ROGUE_PROTOCOLS_XILINX_XVC_SERVER_H__

#include <rogue/protocols/xilinx/SockSd.h>
#include <rogue/protocols/xilinx/JtagDriver.h>
#include <rogue/GeneralError.h>

namespace rogue
{
   namespace protocols
   {
      namespace xilinx
      {
         // XVC Server (top) class
         class XvcServer
         {
            private:

               SockSd     sock_;
               JtagDriver *drv_;
               unsigned   maxMsgSize_;

            public:

               XvcServer(
                         uint16_t    port,
                         JtagDriver* drv,
                         unsigned    maxMsgSize = 32768);

               virtual void run();

               virtual ~XvcServer(){};

               //! Setup class in python
               //static void setup_python();
         };
      }
   }
}

#endif
