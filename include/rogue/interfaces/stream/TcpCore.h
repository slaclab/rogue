/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Stream Network Core
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
#ifndef __ROGUE_INTERFACES_STREAM_TCP_CORE_H__
#define __ROGUE_INTERFACES_STREAM_TCP_CORE_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <atomic>
#include <memory>
#include <string>
#include <thread>

#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"

namespace rogue {
namespace interfaces {
namespace stream {

/**
 * @brief Stream TCP bridge core implementation.
 *
 * @details
 * This class implements the core functionality of the TcpClient and TcpServer
 * classes which implement a Rogue stream bridge over a TCP network. This core
 * can operate in either client or server mode. The TcpClient and TcpServer
 * classes are thin wrappers that define which mode flag to pass to this base
 * class.
 *
 * The TcpServer and TcpClient interfaces are blocking and will stall frame
 * transmissions when the remote side is either not present or is back-pressuring.
 * When the remote server is not present a local buffer is not utilized, where it is
 * utilized when a connection has been established.
 */
class TcpCore : public rogue::interfaces::stream::Master, public rogue::interfaces::stream::Slave {
  protected:
    // Inbound Address
    std::string pullAddr_;

    // Outbound Address
    std::string pushAddr_;

    // Zeromq Context
    void* zmqCtx_;

    // Zeromq inbound port
    void* zmqPull_;

    // Zeromq outbound port
    void* zmqPush_;

    // Thread background
    void runThread();

    // Log
    std::shared_ptr<rogue::Logging> bridgeLog_;

    // Thread
    std::thread* thread_;
    // std::atomic: stop() on caller thread vs runThread() read races on teardown (STREAM-003)
    std::atomic<bool> threadEn_;

    // Lock
    std::mutex bridgeMtx_;

  public:
    /**
     * @brief Creates a TCP stream bridge core instance and returns it as `TcpCorePtr`.
     *
     * @details
     * Parameter semantics are identical to the constructor; see `TcpCore()`
     * for address and port behavior details.
     * This static factory is the preferred construction path when the object
     * is shared across Rogue graph connections or exposed to Python.
     * It returns `std::shared_ptr` ownership compatible with Rogue pointer typedefs.
     * Not exposed to Python.
     *
     * @param addr Interface address for server, remote server address for client.
     * @param port Base TCP port number.
     * @param server Set to `true` to run in server mode.
     * @return Shared pointer to the created bridge core.
     */
    static std::shared_ptr<rogue::interfaces::stream::TcpCore> create(const std::string& addr, uint16_t port, bool server);

    /** @brief Registers this type with Python bindings. */
    static void setup_python();

    /**
     * @brief Constructs a TCP stream bridge core.
     *
     * @details
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` when shared ownership or Python exposure is required.
     *
     * The constructor takes an address, port, and server mode flag. The address
     * can be an IP address or hostname. In server mode, the address selects the
     * local interface to bind. A value of `"*"` binds all local interfaces.
     *
     * The stream bridge uses two consecutive TCP ports; `port` is the base.
     * For example, `port=8000` uses ports `8000` and `8001`.
     *
     * @param addr Interface address for server, remote server address for client.
     * @param port Base TCP port number.
     * @param server Set to `true` to run in server mode.
     */
    TcpCore(const std::string& addr, uint16_t port, bool server);

    /** @brief Destroys the bridge core and releases resources. */
    ~TcpCore();

    /** @brief Closes active bridge connections. */
    void close();

    /** @brief Stops the interface and worker thread. */
    void stop();

    /**
     * @brief Receives a frame from upstream and forwards over the TCP bridge.
     *
     * @param frame Incoming stream frame.
     */
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);
};

/** @brief Shared pointer alias for `TcpCore`. */
typedef std::shared_ptr<rogue::interfaces::stream::TcpCore> TcpCorePtr;

}  // namespace stream
}  // namespace interfaces
};  // namespace rogue

#endif
