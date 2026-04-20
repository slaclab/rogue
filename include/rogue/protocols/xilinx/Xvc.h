/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Rogue implementation of the XVC Server
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
#ifndef __ROGUE_PROTOCOLS_XILINX_XVC_H__
#define __ROGUE_PROTOCOLS_XILINX_XVC_H__
#include "rogue/Directives.h"

#include <atomic>
#include <cstdint>
#include <memory>
#include <thread>

#include "rogue/GeneralError.h"
#include "rogue/Logging.h"
#include "rogue/Queue.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/protocols/xilinx/JtagDriver.h"
#include "rogue/protocols/xilinx/XvcServer.h"

namespace rogue {
namespace protocols {
namespace xilinx {

/**
 * @brief Rogue XVC bridge between TCP XVC clients and Rogue stream transport.
 *
 * @details
 * `Xvc` combines:
 * - `JtagDriver` protocol logic for query/shift operations.
 * - `stream::Master` to send request frames toward hardware transport.
 * - `stream::Slave` to receive reply frames from hardware transport.
 *
 * A background thread runs an `XvcServer` TCP listener for Vivado XVC clients.
 * Incoming XVC operations are translated to driver transfers (`xfer()`), which
 * exchange Rogue frames with downstream transport endpoints.
 */
class Xvc : public rogue::interfaces::stream::Master,
            public rogue::interfaces::stream::Slave,
            public rogue::protocols::xilinx::JtagDriver {
  protected:
    unsigned mtu_;

    // Use rogue frames to exchange data with other rogue objects
    rogue::Queue<std::shared_ptr<rogue::interfaces::stream::Frame>> queue_;

    // Log (named xvcLog_ to avoid shadowing JtagDriver::log_)
    std::shared_ptr<rogue::Logging> xvcLog_;

    // Background server thread.
    std::unique_ptr<std::thread> thread_;
    std::atomic<bool> threadEn_;

    // One-shot start guard.  rogue::Queue::stop() is irreversible (see
    // rogue/Queue.h: stop() sets run_=false with no restart API), so a
    // restarted Xvc would have a permanently-non-blocking queue and a
    // dirty wake-fd.  start() asserts this flag is false; once set, it
    // stays set for the lifetime of the instance.
    std::atomic<bool> started_;

    // Lock
    std::mutex mtx_;

    // Shutdown wake-fd (self-pipe). wakeFd_[0]=read end (consumed by
    // XvcServer/XvcConnection select()); wakeFd_[1]=write end (one byte
    // written in Xvc::stop()).
    int wakeFd_[2] = {-1, -1};

    // Cached bound port (atomic so getPort() is safe during stop()).
    std::atomic<uint32_t> boundPort_{0};

    // Owned XvcServer: constructed in start() so port is synchronously
    // known before the server thread races.
    std::unique_ptr<rogue::protocols::xilinx::XvcServer> server_;

    // TCP server thread entry point for Vivado clients.
    void runThread();

  public:
    /**
     * @brief Creates an XVC bridge instance.
     *
     * @details
     * Parameter semantics are identical to the constructor; see `Xvc()`
     * for bridge-construction details.
     * This static factory is the preferred construction path when the object
     * is shared across Rogue graph connections or exposed to Python.
     * It returns `std::shared_ptr` ownership compatible with Rogue pointer typedefs.
     *
     * @param port TCP port for local XVC server (2542 is the Vivado default; 0 = kernel-assigned).
     * @return Shared pointer to the created XVC instance.
     */
    static std::shared_ptr<rogue::protocols::xilinx::Xvc> create(uint16_t port);

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Constructs an XVC bridge instance.
     *
     * @details
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` when shared ownership or Python exposure is required.
     *
     * @param port TCP port for local XVC server (2542 is the Vivado default; 0 = kernel-assigned).
     */
    explicit Xvc(uint16_t port);

    /** @brief Destroys the XVC bridge instance. */
    ~Xvc();

    /**
     * @brief Starts XVC server thread and enables bridge operation.
     */
    void start();

    /**
     * @brief Stops XVC server thread and drains frame queue.
     */
    void stop();

    /**
     * @brief Receives reply frame from downstream Rogue transport.
     *
     * @details
     * Frames are queued for synchronous consumption by the active XVC transfer.
     *
     * @param frame Incoming frame from downstream transport.
     */
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    /**
     * @brief Returns maximum vector size supported by this XVC bridge.
     *
     * @details
     * Computed from configured MTU and current protocol word size.
     *
     * @return Maximum vector size in bytes.
     */
    uint64_t getMaxVectorSize() final;

    /**
     * @brief Executes one protocol transfer over Rogue frame transport.
     *
     * @details
     * Sends `txBuffer` as a Rogue frame, waits for a queued reply frame, then
     * copies header/payload data into caller buffers.
     *
     * @param txBuffer Request transmit buffer.
     * @param txBytes Number of request bytes.
     * @param hdBuffer Reply header destination buffer.
     * @param hdBytes Number of header bytes to copy.
     * @param rxBuffer Reply payload destination buffer.
     * @param rxBytes Maximum reply payload bytes accepted.
     * @return Number of payload bytes received.
     */
    int xfer(uint8_t* txBuffer,
             unsigned txBytes,
             uint8_t* hdBuffer,
             unsigned hdBytes,
             uint8_t* rxBuffer,
             unsigned rxBytes) final;

    /**
     * @brief Returns the TCP port the XVC server is bound to.
     *
     * @details
     * When port 0 was passed to the constructor, returns the kernel-assigned
     * port after start(); otherwise returns the configured port (typically
     * 2542, the Vivado Hardware Manager default).
     *
     * @return Port number (0 if called before start() when ctor received 0).
     */
    uint32_t getPort() const;
};

// Convenience
typedef std::shared_ptr<rogue::protocols::xilinx::Xvc> XvcPtr;
}  // namespace xilinx
}  // namespace protocols
}  // namespace rogue

#endif
