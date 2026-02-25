/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Memory Server Network Bridge
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
#ifndef __ROGUE_INTERFACES_MEMORY_TCP_SERVER_H__
#define __ROGUE_INTERFACES_MEMORY_TCP_SERVER_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <string>
#include <thread>

#include "rogue/Logging.h"
#include "rogue/interfaces/memory/Master.h"

namespace rogue {
namespace interfaces {
namespace memory {

/**
 * @brief Memory TCP bridge server.
 *
 * @details
 * Implements the server side of the memory TCP bridge.
 *
 * The server receives request messages from remote `TcpClient` instances on a base
 * port and returns completion/result messages on base port + 1. Each inbound request
 * is translated into a local memory transaction executed through this `Master`
 * interface to the attached downstream slave path.
 *
 * Operational behavior:
 * - Request messages carry transaction ID, address, size, type, and optional write data.
 * - Transactions are executed synchronously in the server worker thread.
 * - Responses include returned read data (when applicable) and a status/result string.
 * - The server must bind both bridge ports successfully; binding failures typically
 *   indicate address/port conflicts.
 */
class TcpServer : public rogue::interfaces::memory::Master {
    // Inbound Address
    std::string reqAddr_;

    // Outbound Address
    std::string respAddr_;

    // Zeromq Context
    void* zmqCtx_;

    // Zeromq inbound port
    void* zmqReq_;

    // Zeromq outbound port
    void* zmqResp_;

    // Thread background
    void runThread();

    // Log
    std::shared_ptr<rogue::Logging> bridgeLog_;

    // Thread
    std::thread* thread_;
    bool threadEn_;

  public:
    /**
     * @brief Creates a TCP memory bridge server.
     *
     * @details
     * `addr` may be a hostname, IP address, or `"*"` to bind on all interfaces.
     * The bridge uses two consecutive TCP ports starting at `port` (for example
     * `8000` and `8001`). Exposed as `rogue.interfaces.memory.TcpServer()` in Python.
     *
     * @param addr Local bind address.
     * @param port Base TCP port number.
     * @return Shared pointer to the created server.
     */
    static std::shared_ptr<rogue::interfaces::memory::TcpServer> create(std::string addr, uint16_t port);

    /**
     * @brief Registers this type with Python bindings.
     */
    static void setup_python();

    /**
     * @brief Constructs a TCP memory bridge server.
     *
     * @param addr Local bind address.
     * @param port Base TCP port number.
     */
    TcpServer(std::string addr, uint16_t port);

    /**
     * @brief Destroys the TCP server and releases transport resources.
     */
    ~TcpServer();

    /**
     * @brief Closes bridge connections.
     *
     * @details Deprecated; use `stop()`.
     */
    void close();

    /**
     * @brief Stops the bridge interface and worker thread.
     */
    void stop();
};

/**
 * @brief Shared pointer alias for `TcpServer`.
 */
typedef std::shared_ptr<rogue::interfaces::memory::TcpServer> TcpServerPtr;

}  // namespace memory
}  // namespace interfaces
};  // namespace rogue

#endif
