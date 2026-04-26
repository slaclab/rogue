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

#include <atomic>
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

    void* zmqCtx_  = nullptr;
    void* zmqReq_  = nullptr;
    void* zmqResp_ = nullptr;

    // Thread background
    void runThread();

    // Log
    std::shared_ptr<rogue::Logging> bridgeLog_;

  protected:
    std::thread* thread_ = nullptr;
    std::atomic<bool> threadEn_{false};

  public:
    /**
     * @brief Creates a TCP memory bridge server.
     *
     * @details
     * Parameter semantics are identical to the constructor; see `TcpServer()`
     * for address and port behavior details.
     *
     * Exposed as `rogue.interfaces.memory.TcpServer()` in Python.
     *
     * This static factory is the preferred construction path when the object
     * is shared across Rogue graph connections or exposed to Python.
     * It returns `std::shared_ptr` ownership compatible with Rogue pointer typedefs.
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
     * @details
     * `addr` may be a hostname, IP address, or `"*"` to bind on all interfaces.
     * The bridge uses two consecutive TCP ports starting at `port`; for example,
     * `port=8000` uses ports `8000` and `8001`.
     *
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` when shared ownership or Python exposure is required.
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

    /**
     * @brief Managed-lifecycle startup hook.
     *
     * @details
     * The server binds and starts its worker thread in the constructor, so the
     * managed startup hook is a no-op. It exists so `TcpServer` can
     * participate uniformly in PyRogue managed interface lifecycle handling.
     */
    void start();
};

/**
 * @brief Shared pointer alias for `TcpServer`.
 */
typedef std::shared_ptr<rogue::interfaces::memory::TcpServer> TcpServerPtr;

}  // namespace memory
}  // namespace interfaces
};  // namespace rogue

#endif
