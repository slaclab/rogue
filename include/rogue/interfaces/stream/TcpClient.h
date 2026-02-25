/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Stream Network Client
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
#ifndef __ROGUE_INTERFACES_STREAM_TCP_CLIENT_H__
#define __ROGUE_INTERFACES_STREAM_TCP_CLIENT_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <string>
#include <thread>

#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/interfaces/stream/TcpCore.h"

namespace rogue {
namespace interfaces {
namespace stream {

/**
 * @brief Stream TCP bridge client.
 *
 * @details Thin wrapper around `TcpCore` configured for client mode.
 */
class TcpClient : public rogue::interfaces::stream::TcpCore {
  public:
    /**
     * @brief Creates a TCP stream bridge client and return as TcpClientPtr.
     *
     * @details
     * The creator takes an address and port. The passed server address can either
     * be an IP address or hostname. The stream bridge requires two TCP ports.
     * The passed port is the base number of these two ports. A passed value of 8000
     * will result in both 8000 and 8001 being used by this bridge.
     *
     * Exposed in Python as `rogue.interfaces.stream.TcpClient`.
     * 
     * @param addr Remote server address.
     * @param port Base TCP port number.
     * @return Shared pointer to the created client.
     */
    static std::shared_ptr<rogue::interfaces::stream::TcpClient> create(std::string addr, uint16_t port);

    /** @brief Registers this type with Python bindings. */
    static void setup_python();

    /**
     * @brief Constructs a TCP stream bridge client.
     *
     * @param addr Remote server address.
     * @param port Base TCP port number.
     */
    TcpClient(std::string addr, uint16_t port);

    /** @brief Destroys the TCP client. */
    ~TcpClient();
};

/** @brief Shared pointer alias for `TcpClient`. */
typedef std::shared_ptr<rogue::interfaces::stream::TcpClient> TcpClientPtr;

}  // namespace stream
}  // namespace interfaces
};  // namespace rogue

#endif
