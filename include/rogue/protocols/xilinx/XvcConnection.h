//-----------------------------------------------------------------------------
// Title      : JTAG Support
//-----------------------------------------------------------------------------
// Company    : SLAC National Accelerator Laboratory
//-----------------------------------------------------------------------------
// Description: XvcConnection.h
//-----------------------------------------------------------------------------
// This file is part of 'SLAC Firmware Standard Library'.
// It is subject to the license terms in the LICENSE.txt file found in the
// top-level directory of this distribution and at:
//    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
// No part of 'SLAC Firmware Standard Library', including this file,
// may be copied, modified, propagated, or distributed except according to
// the terms contained in the LICENSE.txt file.
//-----------------------------------------------------------------------------

#ifndef __ROGUE_PROTOCOLS_XILINX_XVC_CONNECTION_H__
#define __ROGUE_PROTOCOLS_XILINX_XVC_CONNECTION_H__

#include <netinet/in.h>
#include <sys/socket.h>

#include "rogue/GeneralError.h"
#include "rogue/protocols/xilinx/JtagDriver.h"

namespace rogue {
namespace protocols {
namespace xilinx {
// Class managing a XVC tcp connection
class XvcConnection {
    int sd_;
    JtagDriver* drv_;
    struct sockaddr_in peer_;

    // just use vectors to back raw memory; DONT use 'size/resize'
    // (unfortunately 'resize' fills elements beyond the current 'size'
    // with zeroes)

    uint8_t* rp_;
    vector<uint8_t> rxb_;
    unsigned long rl_;
    unsigned long tl_;

    vector<uint8_t> txb_;
    unsigned long maxVecLen_;
    unsigned long supVecLen_;
    unsigned long chunk_;

  public:
    XvcConnection(int sd, JtagDriver* drv, unsigned long maxVecLen_ = 32768);

    // fill rx buffer to 'n' octets (from TCP connection)
    virtual void fill(unsigned long n);

    // send tx buffer to TCP connection
    virtual void flush();

    // discard 'n' octets from rx buffer (mark as consumed)
    virtual void bump(unsigned long n);

    // (re)allocated buffers
    virtual void allocBufs();

    virtual void run();

    ssize_t readTo(void* buf, size_t count);

    virtual ~XvcConnection();
};
}  // namespace xilinx
}  // namespace protocols
}  // namespace rogue

#endif
