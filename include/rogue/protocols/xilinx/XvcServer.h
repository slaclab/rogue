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

#ifndef __ROGUE_PROTOCOLS_XILINX_XVC_SERVER_H__
#define __ROGUE_PROTOCOLS_XILINX_XVC_SERVER_H__
#include "rogue/Directives.h"

#include <atomic>
#include <cstdint>

#include "rogue/GeneralError.h"
#include "rogue/Logging.h"
#include "rogue/protocols/xilinx/JtagDriver.h"

namespace rogue {
namespace protocols {
namespace xilinx {
/**
 * @brief TCP listener for XVC client connections.
 *
 * @details
 * `XvcServer` owns the listening socket and accepts one sub-connection at a
 * time. Each accepted client is serviced via `XvcConnection`, which performs
 * XVC protocol parsing and delegates JTAG operations to `JtagDriver`.
 */
class XvcServer {
  private:
    int sd_;
    int wakeFd_;           // shutdown wake-fd (read end), owned by Xvc
    JtagDriver* drv_;
    unsigned maxMsgSize_;
    uint16_t port_;        // kernel-assigned if ctor param was 0

  public:
    /**
     * @brief Constructs an XVC TCP server listener.
     *
     * @param port       Local TCP port to bind (2542 is the Vivado default; 0 = kernel-assigned).
     * @param wakeFd     Read end of the Xvc self-pipe used to break out of select() on shutdown.
     * @param drv        Driver used by accepted connections.
     * @param maxMsgSize Maximum protocol message/vector size in bytes.
     */
    XvcServer(uint16_t port, int wakeFd, JtagDriver* drv, unsigned maxMsgSize = 32768);

    /**
     * @brief Runs accept loop; blocks in select() until accept-ready or wakeFd
     *        readable. Loop continues while threadEn is true.
     *
     * @param threadEn Atomic run-control flag; loop exits when false.
     * @param log      Logger used for connection-level diagnostics.
     */
    virtual void run(std::atomic<bool>& threadEn, rogue::LoggingPtr log);

    /**
     * @brief Returns the TCP port the server is bound to (resolved if port==0 was requested).
     */
    uint32_t getPort() const;

    /** @brief Closes the listening socket and destroys server instance. */
    virtual ~XvcServer();
};
}  // namespace xilinx
}  // namespace protocols
}  // namespace rogue

#endif
