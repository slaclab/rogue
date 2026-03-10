/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Memory Client Network Bridge
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
#ifndef __ROGUE_INTERFACES_MEMORY_TCP_CLIENT_H__
#define __ROGUE_INTERFACES_MEMORY_TCP_CLIENT_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <string>
#include <thread>
#include <condition_variable>

#include "rogue/Logging.h"
#include "rogue/interfaces/memory/Slave.h"

namespace rogue {
namespace interfaces {
namespace memory {

/**
 * @brief Memory TCP bridge client.
 *
 * @details
 * Bridges a local memory transaction source to a remote `TcpServer`.
 *
 * The client accepts transactions through its `Slave` interface and sends them over
 * a two-socket request/response transport (base port and base port + 1). Non-posted
 * transactions are tracked by transaction ID until a response is received by the
 * background thread.
 *
 * Operational behavior:
 * - Write/Post transactions include payload bytes in the outbound message.
 * - Read/Verify transactions send metadata and receive payload bytes in the response.
 * - Posted writes are completed locally after send (no response wait).
 * - If the remote side is unavailable or send path is backpressured, sends may fail
 *   and in-flight transactions can time out at higher layers.
 */
class TcpClient : public rogue::interfaces::memory::Slave {
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

    // Lock
    std::mutex bridgeMtx_;

    // Probe state
    std::mutex probeMtx_;
    std::condition_variable probeCond_;
    uint32_t probeSeq_;
    uint32_t probeId_;
    bool probeDone_;
    std::string probeResult_;
    bool waitReadyOnStart_;

  public:
    /**
     * @brief Creates a TCP memory bridge client.
     *
     * @details
     * Parameter semantics are identical to the constructor; see `TcpClient()`
     * for address and port behavior details.
     * Exposed as `rogue.interfaces.memory.TcpClient()` in Python.
     * This static factory is the preferred construction path when the object
     * is shared across Rogue graph connections or exposed to Python.
     * It returns `std::shared_ptr` ownership compatible with Rogue pointer typedefs.
     *
     * @param addr Remote server address.
     * @param port Base TCP port number.
     * @param waitReady If `true`, configure the instance so `_start()` waits
     *                  for bridge readiness before returning.
     * @return Shared pointer to the created client.
     */
    static std::shared_ptr<rogue::interfaces::memory::TcpClient> create(std::string addr, uint16_t port, bool waitReady = false);

    /**
     * @brief Registers this type with Python bindings.
     */
    static void setup_python();

    /**
     * @brief Constructs a TCP memory bridge client.
     *
     * @details
     * The address is the remote `TcpServer` host (IP or hostname).
     * The bridge uses two consecutive TCP ports starting at `port`; for example,
     * `port=8000` uses ports `8000` and `8001`.
     *
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` when shared ownership or Python exposure is required.
     * `waitReady` does not block in the constructor itself; it configures
     * whether `_start()` should perform readiness probing later.
     *
     * @param addr Remote server address.
     * @param port Base TCP port number.
     * @param waitReady If `true`, record that `_start()` should block until
     *                  the bridge request/response path responds to a
     *                  readiness probe.
     */
    TcpClient(std::string addr, uint16_t port, bool waitReady = false);

    /**
     * @brief Destroys the TCP client and releases transport resources.
     */
    ~TcpClient();

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
     * @brief Wait for the remote TcpServer path to respond to a bridge probe.
     *
     * @details
     * This sends a lightweight internal control transaction through the bridge
     * and waits for the remote `TcpServer` to acknowledge it. It verifies that
     * the request/response path is usable, which is stronger than a local
     * socket-connect state.
     *
     * @param timeout Maximum wait time in seconds.
     * @param period Retry period in seconds.
     * @return `true` if the probe succeeds before timeout, otherwise `false`.
     */
    bool waitReady(double timeout, double period);

    /**
     * @brief Managed-lifecycle startup hook.
     *
     * @details
     * If this instance was constructed with `waitReady=true`, `_start()`
     * blocks until the bridge request/response path responds to a readiness
     * probe. Otherwise it is a no-op.
     */
    void start();

    /**
     * @brief Processes a transaction received from the upstream master.
     *
     * @param tran Transaction to forward to the remote server.
     */
    void doTransaction(std::shared_ptr<rogue::interfaces::memory::Transaction> tran);
};

/**
 * @brief Shared pointer alias for `TcpClient`.
 */
typedef std::shared_ptr<rogue::interfaces::memory::TcpClient> TcpClientPtr;

}  // namespace memory
}  // namespace interfaces
};  // namespace rogue

#endif
