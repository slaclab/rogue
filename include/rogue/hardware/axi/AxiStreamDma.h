/**
  * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 *      AxiStreamDma Interface Class
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
#ifndef __ROGUE_HARDWARE_AXI_AXI_STREAM_DMA_H__
#define __ROGUE_HARDWARE_AXI_AXI_STREAM_DMA_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <atomic>
#include <map>
#include <memory>
#include <string>
#include <thread>

#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"

namespace rogue {
namespace hardware {
namespace axi {

/**
 * Shared descriptor for DMA device state reused across interface instances.
 */
class AxiStreamDmaShared {
  public:
    /**
     * @brief Creates shared DMA descriptor for a device path.
     * @param path Device path, for example `/dev/datadev_0`.
     */
    explicit AxiStreamDmaShared(std::string path);

    // Shared driver file descriptor used for DMA buffer mapping.
    int32_t fd;

    // Device path.
    std::string path;

    // Number of active AxiStreamDma instances using this descriptor.
    int32_t openCount;

    // Pointer array to mapped DMA buffers for zero-copy mode.
    void** rawBuff;

    // Number of mapped DMA buffers.
    uint32_t bCount;

    // DMA buffer size in bytes.
    uint32_t bSize;

    // Zero-copy mode enabled for this path.
    bool zCopyEn;
};

/** Alias for shared pointer to `AxiStreamDmaShared`. */
typedef std::shared_ptr<rogue::hardware::axi::AxiStreamDmaShared> AxiStreamDmaSharedPtr;

/**
 * @brief Bridge between Rogue stream interfaces and AXI Stream DMA drivers.
 *
 * @details
 * `AxiStreamDma` connects Rogue `stream::Master`/`stream::Slave` APIs to the
 * aes-stream-driver kernel interface. It supports:
 * - RX path: DMA buffers received from hardware and forwarded as Rogue frames.
 * - TX path: Rogue frames written to hardware via DMA.
 * - Optional zero-copy buffer mapping when supported by the driver/path.
 *
 * Threading model:
 * - A background RX thread is started in the constructor and runs until `stop()`
 *   or destruction.
 * - TX operations execute synchronously in caller context of `acceptFrame()`.
 *
 * Zero-copy model:
 * - Enabled by default per device path.
 * - `zeroCopyDisable(path)` must be called before first instance on that path.
 * - When disabled or unavailable, frame buffers are allocated from local pool
 *   and copied on TX/RX boundaries.
 */
class AxiStreamDma : public rogue::interfaces::stream::Master, public rogue::interfaces::stream::Slave {
    // Shared mapped-buffer descriptor cache by device path.
    static std::map<std::string, std::shared_ptr<rogue::hardware::axi::AxiStreamDmaShared> > sharedBuffers_;

    // Maximum number of buffers to receive in one DMA call.
    static const uint32_t RxBufferCount = 100;

    // Shared descriptor state for this path.
    std::shared_ptr<rogue::hardware::axi::AxiStreamDmaShared> desc_;

    // Process-local descriptor for TX/RX operations and dest mask programming.
    int32_t fd_;

    // Destination selector used when transmitting frames.
    uint32_t dest_;

    // TX/alloc select timeout.
    struct timeval timeout_;

    // SSI flag handling enable.
    bool enSsi_;

  protected:
    std::thread* thread_ = nullptr;
    std::atomic<bool> threadEn_{false};

  private:
    // Logger instance.
    std::shared_ptr<rogue::Logging> log_;

    // RX worker thread entry point.
    void runThread(std::weak_ptr<int>);

    // Deferred DMA buffer return queue.
    rogue::Queue<uint32_t> retQueue_;

    // Threshold for draining return queue.
    uint32_t retThold_;

    // Opens/reuses shared DMA mapping state for a device path.
    static std::shared_ptr<rogue::hardware::axi::AxiStreamDmaShared> openShared(std::string path,
                                                                                std::shared_ptr<rogue::Logging> log);

    // Closes shared DMA mapping state when last user exits.
    static void closeShared(std::shared_ptr<rogue::hardware::axi::AxiStreamDmaShared>);

  public:
    /**
     * @brief Creates an AXI Stream DMA bridge instance.
     *
     * @details
     * Parameter semantics are identical to the constructor; see `AxiStreamDma()`
     * for destination and SSI behavior details.
     * Exposed to Python as `rogue.hardware.axi.AxiStreamDma(...)`.
     * This static factory is the preferred construction path when the object
     * is shared across Rogue graph connections or exposed to Python.
     * It returns `std::shared_ptr` ownership compatible with Rogue pointer typedefs.
     *
     * @param path Path to device, for example `/dev/datadev_0`.
     * @param dest Destination index for DMA transactions.
     * @param ssiEnable Enable SSI user-field handling.
     * @return Shared pointer to the created interface.
     */
    static std::shared_ptr<rogue::hardware::axi::AxiStreamDma> create(std::string path, uint32_t dest, bool ssiEnable);

    /**
     * @brief Disables zero-copy mode for a device path.
     *
     * @details
     * Must be called before the first `AxiStreamDma` instance for `path`.
     *
     * By default, the class attempts to map kernel DMA buffers directly into
     * user space and use those buffers as Rogue frame storage (zero-copy path).
     * This reduces copies and CPU overhead. When disabled, Rogue allocates
     * local pooled buffers and copies data to/from driver buffers.
     *
     * Exposed to Python as `zeroCopyDisable()`.
     * @param path Device path, for example `/dev/datadev_0`.
     */
    static void zeroCopyDisable(std::string path);

    /**
     * @brief Registers Python bindings for this class.
     */
    static void setup_python();

    /**
     * @brief Constructs an AXI stream DMA bridge.
     *
     * @details
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` when shared ownership or Python exposure is required.
     *
     * The destination field is an AXI Stream sideband routing value. Usage is
     * driver/firmware specific, but a common mapping is:
     * - low 8 bits: AXI `tDest` value carried with the stream frame
     * - upper bits: DMA channel selection/indexing in lower-level hardware
     *
     * `ssiEnable` controls insertion/interpretation of SLAC SSI user bits:
     * - SOF marker in first-user field bit 1
     * - EOFE marker in last-user field bit 0
     *
     * @param path Device path, for example `/dev/datadev_0`.
     * @param dest Destination index used for DMA transactions.
     * @param ssiEnable Enable SSI user-field handling.
     */
    AxiStreamDma(std::string path, uint32_t dest, bool ssiEnable);

    /** @brief Destroys the interface and stops background activity. */
    ~AxiStreamDma();

    /** @brief Stops RX thread and closes DMA file descriptors. */
    void stop();

    /**
     * @brief Sets TX/alloc wait timeout.
     *
     * @details
     * The timeout is used in blocking select loops for outbound DMA resources.
     * On timeout, warnings are logged and retries continue until resources are
     * available.
     *
     * Exposed to Python as `setTimeout()`.
     * @param timeout Timeout value in microseconds.
     */
    void setTimeout(uint32_t timeout);

    /**
     * @brief Sets DMA driver debug level.
     *
     * @details
     * Forwards `level` to lower-level driver debug control. Driver messages
     * can be inspected through kernel logs (for example `dmesg`). Typical
     * drivers treat any positive value as debug enabled.
     *
     * Exposed to Python as `setDriverDebug()`.
     * @param level Driver debug level.
     */
    void setDriverDebug(uint32_t level);

    /**
     * @brief Sends an ACK strobe through driver-specific DMA control path.
     *
     * @details
     * Hardware behavior is implementation-specific to the target DMA core.
     * Exposed to Python as `dmaAck()`.
     */
    void dmaAck();

    /**
     * @brief Allocates a frame for upstream writers.
     *
     * @details
     * In zero-copy mode, this may allocate one or more DMA-backed buffers and
     * append them into a single frame until `size` is satisfied. If zero-copy
     * is disabled (globally for the path or per-request via `zeroCopyEn`),
     * allocation falls back to local frame buffers.
     *
     * @param size Minimum requested payload size in bytes.
     * @param zeroCopyEn `true` to allow zero-copy allocation when possible.
     * @return Newly allocated frame.
     */
    std::shared_ptr<rogue::interfaces::stream::Frame> acceptReq(uint32_t size, bool zeroCopyEn);

    /**
     * @brief Accepts a frame for DMA transmit.
     *
     * @details
     * The frame may contain DMA-backed buffers (zero-copy) and/or local buffers.
     * In SSI mode, SOF/EOFE bits are inserted into user fields for first/last
     * buffer segments as required by the protocol.
     *
     * @param frame Input frame to transmit.
     */
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    /**
     * @brief Returns DMA-backed buffer memory after frame release.
     * @param data Buffer data pointer.
     * @param meta Driver-specific metadata/index.
     * @param rawSize Original allocated buffer size in bytes.
     */
    void retBuffer(uint8_t* data, uint32_t meta, uint32_t rawSize);

    /**
     * @brief Gets DMA driver Git version string.
     * @return Git version string, empty on failure.
     */
    std::string getGitVersion();

    /**
     * @brief Gets DMA driver API version.
     * @return Driver API version number.
     */
    uint32_t getApiVersion();

    /**
     * @brief Gets DMA buffer size.
     * @return RX/TX DMA buffer size in bytes.
     */
    uint32_t getBuffSize();

    /**
     * @brief Gets RX DMA buffer count.
     * @return Number of RX buffers.
     */
    uint32_t getRxBuffCount();

    /**
     * @brief Gets RX buffers currently held by user space.
     * @return RX in-user count.
     */
    uint32_t getRxBuffinUserCount();

    /**
     * @brief Gets RX buffers currently held by hardware.
     * @return RX in-hardware count.
     */
    uint32_t getRxBuffinHwCount();

    /**
     * @brief Gets RX buffers queued before hardware.
     * @return RX pre-hardware queue count.
     */
    uint32_t getRxBuffinPreHwQCount();

    /**
     * @brief Gets RX buffers queued in software.
     * @return RX software queue count.
     */
    uint32_t getRxBuffinSwQCount();

    /**
     * @brief Gets RX buffer missing count.
     * @return RX missing buffer count.
     */
    uint32_t getRxBuffMissCount();

    /**
     * @brief Gets TX DMA buffer count.
     * @return Number of TX buffers.
     */
    uint32_t getTxBuffCount();

    /**
     * @brief Gets TX buffers currently held by user space.
     * @return TX in-user count.
     */
    uint32_t getTxBuffinUserCount();

    /**
     * @brief Gets TX buffers currently held by hardware.
     * @return TX in-hardware count.
     */
    uint32_t getTxBuffinHwCount();

    /**
     * @brief Gets TX buffers queued before hardware.
     * @return TX pre-hardware queue count.
     */
    uint32_t getTxBuffinPreHwQCount();

    /**
     * @brief Gets TX buffers queued in software.
     * @return TX software queue count.
     */
    uint32_t getTxBuffinSwQCount();

    /**
     * @brief Gets TX buffer missing count.
     * @return TX missing buffer count.
     */
    uint32_t getTxBuffMissCount();
};

/** Alias for shared pointer to `AxiStreamDma`. */
typedef std::shared_ptr<rogue::hardware::axi::AxiStreamDma> AxiStreamDmaPtr;

}  // namespace axi
}  // namespace hardware
};  // namespace rogue

#endif
