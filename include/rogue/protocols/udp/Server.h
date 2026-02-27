/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * UDP Server
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
#ifndef __ROGUE_PROTOCOLS_UDP_SERVER_H__
#define __ROGUE_PROTOCOLS_UDP_SERVER_H__
#include "rogue/Directives.h"

#include <netdb.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <stdint.h>
#include <sys/socket.h>

#include <memory>
#include <thread>

#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/protocols/udp/Core.h"

namespace rogue {
namespace protocols {
namespace udp {

/**
 * @brief UDP stream endpoint that listens on a local UDP port.
 *
 * @details
 * `Server` combines UDP transport (`udp::Core`) with Rogue stream interfaces:
 * - `stream::Slave`: accepts outbound frames and transmits datagrams to the
 *   most recently seen remote endpoint.
 * - `stream::Master`: emits inbound datagrams as Rogue frames.
 *
 * A background receive thread listens on the bound UDP socket, forwards payloads
 * as frames, and updates remote endpoint address when packets are received.
 */
class Server : public rogue::protocols::udp::Core,
               public rogue::interfaces::stream::Master,
               public rogue::interfaces::stream::Slave {
    // Bound local UDP port.
    uint16_t port_;

    // Local bind socket address.
    struct sockaddr_in locAddr_;

    // Background receive thread entry point.
    void runThread(std::weak_ptr<int>);

  public:
    /**
     * @brief Creates a UDP server endpoint.
     *
     * @details
     * Parameter semantics are identical to the constructor; see `Server()`
     * for endpoint setup behavior details.
     * This static factory is the preferred construction path when the object
     * is shared across Rogue graph connections or exposed to Python.
     * It returns `std::shared_ptr` ownership compatible with Rogue pointer typedefs.
     *
     * @param port Local UDP port to bind (0 requests dynamic port assignment).
     * @param jumbo `true` for jumbo payload sizing; `false` for standard MTU.
     * @return Shared pointer to the created server.
     */
    static std::shared_ptr<rogue::protocols::udp::Server> create(uint16_t port, bool jumbo);

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Constructs a UDP server endpoint.
     *
     * @details
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` when shared ownership or Python exposure is required.
     *
     * Creates and binds UDP socket, initializes frame pool sizing, and starts
     * background receive thread. If `port == 0`, the OS-assigned port is queried
     * and stored.
     *
     * @param port Local UDP port to bind (0 requests dynamic port assignment).
     * @param jumbo `true` for jumbo payload sizing; `false` for standard MTU.
     */
    Server(uint16_t port, bool jumbo);

    /** @brief Destroys the UDP server endpoint. */
    ~Server();

    /**
     * @brief Stops the UDP server endpoint.
     *
     * @details
     * Stops receive thread, joins thread, and closes socket.
     */
    void stop();

    /**
     * @brief Returns bound local UDP port number.
     *
     * @return Local UDP port.
     */
    uint32_t getPort();

    /**
     * @brief Accepts an outbound stream frame and transmits it as UDP datagrams.
     *
     * @details
     * Datagrams are sent to the current remote endpoint address learned by the
     * receive thread. Writes use `select()` with configured timeout.
     *
     * @param frame Outbound frame to transmit.
     */
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);
};

// Convenience
typedef std::shared_ptr<rogue::protocols::udp::Server> ServerPtr;

}  // namespace udp
}  // namespace protocols
};  // namespace rogue

#endif
