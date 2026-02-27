/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 *      Raw Memory Mapped Access
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
#ifndef __ROGUE_HARDWARE_MEM_MAP_H__
#define __ROGUE_HARDWARE_MEM_MAP_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <mutex>
#include <thread>

#include "rogue/Logging.h"
#include "rogue/Queue.h"
#include "rogue/interfaces/memory/Slave.h"
#include "rogue/interfaces/memory/Transaction.h"

#define MAP_DEVICE "/dev/mem"

namespace rogue {
namespace hardware {

/**
 * @brief Memory-slave bridge for direct `/dev/mem` mapped register access.
 *
 * @details
 * `MemMap` maps a physical address range from Linux `/dev/mem` into user space
 * and services Rogue memory transactions against that mapped region.
 *
 * Transaction flow:
 * - `doTransaction()` enqueues requests from upstream memory masters.
 * - A worker thread dequeues transactions and performs 32-bit word accesses.
 * - Read/verify requests copy mapped values into transaction buffer.
 * - Write/post requests copy transaction buffer values into mapped memory.
 *
 * This class is intended for environments where raw memory mapping is
 * permitted and safe for the target platform.
 */
class MemMap : public rogue::interfaces::memory::Slave {
    // `/dev/mem` file descriptor.
    int32_t fd_;

    // Mapped region size in bytes.
    uint64_t size_;

    // Base pointer of mapped memory region.
    volatile uint8_t* map_;

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
     * @brief Creates a raw memory-map bridge instance.
     *
     * @details
     * Parameter semantics are identical to the constructor; see `MemMap()`
     * for mapping and worker-thread setup details.
     * Exposed to Python as `rogue.hardware.MemMap()`.
     * This static factory is the preferred construction path when the object
     * is shared across Rogue graph connections or exposed to Python.
     * It returns `std::shared_ptr` ownership compatible with Rogue pointer typedefs.
     *
     * @param base Physical base address to map.
     * @param size Size of address space to map in bytes.
     * @return Shared pointer to the created `MemMap`.
     */
    static std::shared_ptr<rogue::hardware::MemMap> create(uint64_t base, uint32_t size);

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Constructs a raw memory-map bridge instance.
     *
     * @details
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` when shared ownership or Python exposure is required.
     *
     * Opens `/dev/mem`, maps the requested physical range, and starts worker
     * thread for queued transaction processing.
     *
     * @param base Physical base address to map.
     * @param size Size of address space to map in bytes.
     */
    MemMap(uint64_t base, uint32_t size);

    /** @brief Destroys the raw memory-map bridge instance. */
    ~MemMap();

    /**
     * @brief Stops worker thread, unmaps memory, and closes `/dev/mem`.
     */
    void stop();

    /**
     * @brief Queues a memory transaction for asynchronous mapped-memory access.
     *
     * @param tran Transaction received from upstream memory master.
     */
    void doTransaction(std::shared_ptr<rogue::interfaces::memory::Transaction> tran);
};

/** @brief Shared pointer alias for `MemMap`. */
typedef std::shared_ptr<rogue::hardware::MemMap> MemMapPtr;

}  // namespace hardware
};  // namespace rogue

#endif
