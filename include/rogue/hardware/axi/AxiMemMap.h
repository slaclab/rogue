/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 *      AXI Memory Mapped Access
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
#ifndef __ROGUE_HARDWARE_AXI_MEM_MAP_H__
#define __ROGUE_HARDWARE_AXI_MEM_MAP_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <mutex>
#include <string>
#include <thread>

#include "rogue/Logging.h"
#include "rogue/Queue.h"
#include "rogue/interfaces/memory/Slave.h"
#include "rogue/interfaces/memory/Transaction.h"

namespace rogue {
namespace hardware {
namespace axi {

/**
 * @brief Memory-slave bridge for AXI register access via aes-stream-driver.
 *
 * @details
 * `AxiMemMap` is Rogue's wrapper around the AES stream drivers kernel/user API:
 * https://github.com/slaclab/aes-stream-drivers
 *
 * It adapts Rogue memory transactions to the driver register access calls
 * (`dmaReadRegister`/`dmaWriteRegister`). This enables read/write transactions
 * to PCIe register space (for example via the `datadev` driver) or Zynq AXI4
 * register space (for example via `axi_memory_map`), depending on what the loaded
 * driver exposes.
 *
 * Transaction flow:
 * - `doTransaction()` enqueues requests from upstream memory masters.
 * - A worker thread dequeues transactions and executes 32-bit register accesses.
 * - Read data is copied back into the transaction buffer.
 * - Each transaction completes with `done()` or `error(...)`.
 *
 * Multiple `AxiMemMap` instances may be attached to the same underlying driver.
 */
class AxiMemMap : public rogue::interfaces::memory::Slave {
    // AxiMemMap device file descriptor.
    int32_t fd_;

    // Logging
    std::shared_ptr<rogue::Logging> log_;

    std::thread* thread_;
    bool threadEn_;

    // Background worker thread entry point.
    void runThread();

    // Queue
    rogue::Queue<std::shared_ptr<rogue::interfaces::memory::Transaction>> queue_;

  public:
    /**
     * @brief Creates an AXI memory-map bridge instance.
     *
     * @details
     * Exposed to Python as `rogue.hardware.axi.AxiMemMap()`.
     *
     * @param path Device path (for example `/dev/datadev_0`).
     * @return Shared pointer to the created `AxiMemMap`.
     */
    static std::shared_ptr<rogue::hardware::axi::AxiMemMap> create(std::string path);

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Constructs an AXI memory-map bridge instance.
     *
     * @details
     * Opens driver device, validates driver API compatibility, and starts worker
     * thread for queued transaction processing.
     *
     * @param path Device path (for example `/dev/datadev_0`).
     */
    explicit AxiMemMap(std::string path);

    /** @brief Destroys the AXI memory-map bridge instance. */
    ~AxiMemMap();

    /**
     * @brief Stops worker thread and closes device handle.
     */
    void stop();

    /**
     * @brief Queues a memory transaction for asynchronous register execution.
     *
     * @param tran Transaction received from upstream memory master.
     */
    void doTransaction(std::shared_ptr<rogue::interfaces::memory::Transaction> tran);
};

/** @brief Shared pointer alias for `AxiMemMap`. */
typedef std::shared_ptr<rogue::hardware::axi::AxiMemMap> AxiMemMapPtr;

}  // namespace axi
}  // namespace hardware
};  // namespace rogue

#endif
