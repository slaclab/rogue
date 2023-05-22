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
#include <rogue/Directives.h>

#include <rogue/GeneralError.h>
#include <rogue/Logging.h>
#include <rogue/protocols/xilinx/JtagDriver.h>

namespace rogue {
namespace protocols {
namespace xilinx {
// XVC Server (top) class
class XvcServer {
  private:
    int sd_;
    JtagDriver* drv_;
    unsigned maxMsgSize_;

  public:
    XvcServer(uint16_t port, JtagDriver* drv, unsigned maxMsgSize = 32768);

    virtual void run(bool& threadEn, rogue::LoggingPtr log);

    virtual ~XvcServer();
};
}  // namespace xilinx
}  // namespace protocols
}  // namespace rogue

#endif
