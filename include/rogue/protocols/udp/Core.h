/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
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
#include "rogue/Directives.h"

#include <netdb.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <stdint.h>
#include <sys/socket.h>

#include <atomic>
#include <memory>

#include "rogue/Logging.h"

namespace rogue {
namespace protocols {
namespace udp {

/** @brief Jumbo-frame MTU in bytes (`9000`). */
const uint32_t JumboMTU = 9000;
/** @brief Standard Ethernet MTU in bytes (`1500`). */
const uint32_t StdMTU   = 1500;

// IPv4 Header = 20B, UDP Header = 8B
/** @brief Combined IPv4 + UDP header size in bytes. */
const uint32_t HdrSize = 20 + 8;

/** @brief Maximum UDP payload for jumbo MTU (`9000 - 28 = 8972` bytes). */
const uint32_t MaxJumboPayload = JumboMTU - HdrSize;
/** @brief Maximum UDP payload for standard MTU (`1500 - 28 = 1472` bytes). */
const uint32_t MaxStdPayload   = StdMTU - HdrSize;

/**
 * @brief Shared UDP transport base for stream client/server endpoints.
 *
 * @details
 * `Core` contains common socket and transport configuration used by UDP stream
 * endpoints. It centralizes payload sizing (`jumbo` vs standard MTU), socket
 * timeout configuration for transmit operations, receive-buffer sizing, and
 * shared synchronization primitives used by derived classes.
 *
 * Concrete data-path behavior (background receive thread, stream callbacks, and
 * socket lifecycle) is implemented by `udp::Client` and `udp::Server`.
 */
class Core {
  protected:
    std::shared_ptr<rogue::Logging> udpLog_;

    // Jumbo-frame enable state.
    bool jumbo_;

    // Socket descriptor.
    int32_t fd_;

    // Peer socket address.
    struct sockaddr_in remAddr_;

    // Transmit select()/send timeout.
    struct timeval timeout_;

    std::thread* thread_;
    // std::atomic: stop() on caller thread vs runThread() read races on teardown (PROTO-UDP-001)
    std::atomic<bool> threadEn_;

    // Synchronizes shared socket/address updates in derived classes.
    std::mutex udpMtx_;

  public:
    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Constructs shared UDP core state.
     *
     * @param jumbo `true` to use jumbo-payload sizing; `false` for standard MTU.
     */
    explicit Core(bool jumbo);

    /** @brief Destroys the UDP core instance. */
    ~Core();

    /**
     * @brief Stops the UDP interface.
     *
     * @details
     * Derived classes provide socket/thread shutdown behavior.
     */
    void stop();

    /**
     * @brief Returns maximum UDP payload size in bytes.
     *
     * @details
     * Returns:
     * - `8972` bytes when jumbo mode is enabled (`MTU 9000`).
     * - `1472` bytes when jumbo mode is disabled (`MTU 1500`).
     *
     * @return Maximum payload size for configured MTU mode.
     */
    uint32_t maxPayload();

    /**
     * @brief Requests kernel UDP receive-buffer sizing by packet count.
     *
     * @details
     * Computes `count * mtu` bytes and programs `SO_RCVBUF`. Returns `false`
     * if the kernel effective receive buffer is smaller than requested.
     *
     * @param count Number of packets worth of RX buffering to request.
     * @return `true` if effective buffer size meets/exceeds request.
     */
    bool setRxBufferCount(uint32_t count);

    /**
     * @brief Sets outbound transmit wait timeout.
     *
     * @details
     * Timeout is specified in microseconds and converted to `timeval` for
     * `select()`-based write readiness checks in derived endpoints.
     *
     * @param timeout Timeout in microseconds.
     */
    void setTimeout(uint32_t timeout);
};

// Convenience
typedef std::shared_ptr<rogue::protocols::udp::Core> CorePtr;
}  // namespace udp
}  // namespace protocols
};  // namespace rogue

#endif
