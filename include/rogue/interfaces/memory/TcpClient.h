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

  public:
    /**
     * @brief Creates a TCP memory bridge client.
     *
     * @details
     * The address is the remote `TcpServer` host (IP or hostname). The bridge uses
     * two consecutive TCP ports starting at `port` (for example `8000` and `8001`).
     * Exposed as `rogue.interfaces.memory.TcpClient()` in Python.
     *
     * @param addr Remote server address.
     * @param port Base TCP port number.
     * @return Shared pointer to the created client.
     */
    static std::shared_ptr<rogue::interfaces::memory::TcpClient> create(std::string addr, uint16_t port);

    /**
     * @brief Registers this type with Python bindings.
     */
    static void setup_python();

    /**
     * @brief Constructs a TCP memory bridge client.
     *
     * @param addr Remote server address.
     * @param port Base TCP port number.
     */
    TcpClient(std::string addr, uint16_t port);

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
