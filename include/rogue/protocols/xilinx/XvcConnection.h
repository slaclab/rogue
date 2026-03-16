/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 *      JTAG Support
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

#ifndef __ROGUE_PROTOCOLS_XILINX_XVC_CONNECTION_H__
#define __ROGUE_PROTOCOLS_XILINX_XVC_CONNECTION_H__
#include "rogue/Directives.h"

#include <netinet/in.h>
#include <sys/socket.h>

#include <vector>

#include "rogue/GeneralError.h"
#include "rogue/protocols/xilinx/JtagDriver.h"

namespace rogue {
namespace protocols {
namespace xilinx {
/**
 * @brief Manages one TCP client connection speaking the XVC protocol.
 *
 * @details
 * `XvcConnection` parses XVC commands (`getinfo`, `settck`, `shift`) from a
 * connected socket, dispatches JTAG operations through `JtagDriver`, and sends
 * protocol responses back to the TCP client.
 */
class XvcConnection {
    int sd_;
    JtagDriver* drv_;
    struct sockaddr_in peer_;

    // just use vectors to back raw memory; DONT use 'size/resize'
    // (unfortunately 'resize' fills elements beyond the current 'size'
    // with zeroes)

    uint8_t* rp_;
    vector<uint8_t> rxb_;
    uint64_t rl_;
    uint64_t tl_;

    vector<uint8_t> txb_;
    uint64_t maxVecLen_;
    uint64_t supVecLen_;
    uint64_t chunk_;

  public:
    /**
     * @brief Accepts and initializes a new XVC TCP sub-connection.
     *
     * @param sd Listening socket descriptor.
     * @param drv Driver used to execute JTAG operations.
     * @param maxVecLen Maximum vector length in bytes accepted from client.
     */
    XvcConnection(int sd, JtagDriver* drv, uint64_t maxVecLen_ = 32768);

    /**
     * @brief Ensures at least `n` bytes are available in RX buffer.
     *
     * @param n Required number of bytes.
     */
    virtual void fill(uint64_t n);

    /**
     * @brief Flushes pending TX buffer bytes to socket.
     */
    virtual void flush();

    /**
     * @brief Marks `n` RX bytes as consumed.
     *
     * @param n Number of bytes to consume.
     */
    virtual void bump(uint64_t n);

    /**
     * @brief Allocates/reinitializes internal RX/TX buffers.
     */
    virtual void allocBufs();

    /**
     * @brief Runs command processing loop for this connection.
     */
    virtual void run();

    /**
     * @brief Reads up to `count` bytes with timeout.
     *
     * @param buf Destination buffer.
     * @param count Maximum bytes to read.
     * @return Number of bytes read, or `0` on timeout/no data.
     */
    ssize_t readTo(void* buf, size_t count);

    /** @brief Closes this XVC TCP sub-connection. */
    virtual ~XvcConnection();
};
}  // namespace xilinx
}  // namespace protocols
}  // namespace rogue

#endif
