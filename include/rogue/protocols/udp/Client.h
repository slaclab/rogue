/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * UDP Client
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
#ifndef __ROGUE_PROTOCOLS_UDP_CLIENT_H__
#define __ROGUE_PROTOCOLS_UDP_CLIENT_H__
#include "rogue/Directives.h"

#include <netdb.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <stdint.h>
#include <sys/socket.h>

#include <memory>
#include <string>
#include <thread>

#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/protocols/udp/Core.h"

namespace rogue {
namespace protocols {
namespace udp {

/**
 * @brief UDP stream endpoint that sends to and receives from a remote host.
 *
 * @details
 * `Client` combines UDP transport (`udp::Core`) with Rogue stream interfaces:
 * - `stream::Slave`: accepts outbound frames and transmits them as UDP datagrams.
 * - `stream::Master`: emits received UDP datagrams as Rogue frames.
 *
 * A background receive thread continuously reads datagrams and forwards them
 * downstream as frames from the local frame pool.
 */
class Client : public rogue::protocols::udp::Core,
               public rogue::interfaces::stream::Master,
               public rogue::interfaces::stream::Slave {
    // Remote hostname or IPv4 address string.
    std::string address_;

    // Remote UDP port.
    uint16_t port_;

    // Background receive thread entry point.
    void runThread(std::weak_ptr<int>);

  public:
    /**
     * @brief Creates a UDP client endpoint.
     *
     * @param host Remote hostname or IPv4 address.
     * @param port Remote UDP port.
     * @param jumbo `true` for jumbo payload sizing; `false` for standard MTU.
     * @return Shared pointer to the created client.
     */
    static std::shared_ptr<rogue::protocols::udp::Client> create(std::string host, uint16_t port, bool jumbo);

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Constructs a UDP client endpoint.
     *
     * @details
     * Resolves host address, creates UDP socket, initializes frame pool sizing,
     * and starts background receive thread.
     *
     * @param host Remote hostname or IPv4 address.
     * @param port Remote UDP port.
     * @param jumbo `true` for jumbo payload sizing; `false` for standard MTU.
     */
    Client(std::string host, uint16_t port, bool jumbo);

    /** @brief Destroys the UDP client endpoint. */
    ~Client();

    /**
     * @brief Stops the UDP client endpoint.
     *
     * @details
     * Stops receive thread, joins thread, and closes socket.
     */
    void stop();

    /**
     * @brief Accepts an outbound stream frame and transmits it as UDP datagrams.
     *
     * @details
     * Each non-empty frame buffer payload is sent as a UDP datagram. Writes use
     * `select()` with configured timeout; timeout/failure is logged.
     *
     * @param frame Outbound frame to transmit.
     */
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);
};

// Convenience
typedef std::shared_ptr<rogue::protocols::udp::Client> ClientPtr;

}  // namespace udp
}  // namespace protocols
};  // namespace rogue

#endif
