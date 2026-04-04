/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    SLAC Register Protocol (SRP) SrpV3 Server
 *-----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to
 * the license terms in the LICENSE.txt file found in the top-level directory
 * of this distribution and at:
 * https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
 * No part of the rogue software platform, including this file, may be
 * copied, modified, propagated, or distributed except according to the terms
 * contained in the LICENSE.txt file.
 *-----------------------------------------------------------------------------
 **/
#ifndef __ROGUE_PROTOCOLS_SRP_SRPV3SERVER_H__
#define __ROGUE_PROTOCOLS_SRP_SRPV3SERVER_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <condition_variable>
#include <map>
#include <memory>
#include <mutex>
#include <queue>
#include <thread>

#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"

namespace rogue {
namespace protocols {
namespace srp {

/**
 * @brief Software SRPv3 server that emulates a hardware SRP endpoint.
 *
 * @details
 * `SrpV3Server` acts as the remote endpoint of the SRPv3 protocol,
 * receiving SRPv3 request frames and producing SRPv3 response frames.
 * It maintains an internal memory space, enabling full software-only
 * testing of the SRPv3 protocol path without FPGA or ASIC hardware.
 *
 * Typical CI/test usage connects `SrpV3` (the client/master) to
 * `SrpV3Server` via a bidirectional stream path:
 *
 * @code
 *   SrpV3 (client) == SrpV3Server (server)
 * @endcode
 *
 * When a request frame arrives via `acceptFrame()`, the server queues
 * the frame for processing on an internal worker thread. The worker:
 * 1. Decodes the SRPv3 header (version, opcode, transaction ID, address, size).
 * 2. For write/post requests: copies payload data into internal memory.
 * 3. For read requests: copies data from internal memory into the response.
 * 4. Builds and sends a response frame with the original header and a zero
 *    status tail (indicating success).
 * 5. For posted writes, no response frame is sent.
 *
 * The worker thread avoids a deadlock that would occur if response frames
 * were sent synchronously inside `acceptFrame()`, since `SrpV3` holds
 * a transaction lock during its `doTransaction()` call chain.
 *
 * Memory is allocated on demand in 4 KiB pages, similar to
 * `rogue::interfaces::memory::Emulate`.
 *
 * Threading/locking model:
 * - `acceptFrame()` queues frames and returns immediately.
 * - A dedicated worker thread dequeues and processes frames serially.
 * - Internal memory map access is protected by a mutex.
 *
 * Protocol reference:
 * https://confluence.slac.stanford.edu/x/cRmVD
 */
class SrpV3Server : public rogue::interfaces::stream::Master,
                    public rogue::interfaces::stream::Slave {
    std::shared_ptr<rogue::Logging> log_;

    static const uint32_t HeadLen = 20;
    static const uint32_t TailLen = 4;

    // Memory map type: 4K-aligned base address -> 4K page
    typedef std::map<uint64_t, uint8_t*> MemoryMap;

    // Internal memory emulation
    MemoryMap memMap_;

    // Memory access mutex
    std::mutex memMtx_;

    // Allocation tracking
    uint32_t totAlloc_;

    // Worker thread and queue
    std::thread thread_;
    std::queue<std::shared_ptr<rogue::interfaces::stream::Frame> > queue_;
    std::mutex queMtx_;
    std::condition_variable queCond_;
    bool threadEn_;

    //! Worker thread function
    void runThread();

    //! Process a single request frame and send response
    void processFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

  public:
    /**
     * @brief Creates an SRP v3 server instance.
     *
     * @details
     * This static factory is the preferred construction path when the object
     * is shared across Rogue graph connections or exposed to Python.
     * It returns `std::shared_ptr` ownership compatible with Rogue pointer typedefs.
     *
     * @return Shared pointer to the created `SrpV3Server`.
     */
    static std::shared_ptr<rogue::protocols::srp::SrpV3Server> create();

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Constructs an SRP v3 server instance.
     *
     * @details
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` when shared ownership or Python exposure is required.
     * Starts an internal worker thread for processing queued request frames.
     */
    SrpV3Server();

    /** @brief Destroys the SRP v3 server instance and frees allocated memory. */
    ~SrpV3Server();

    /**
     * @brief Stops the worker thread.
     *
     * @details
     * Called during shutdown to cleanly stop the processing thread.
     */
    void stop();

    /**
     * @brief Queues an incoming SRP v3 request frame for processing.
     *
     * @details
     * The frame is added to an internal queue and processed asynchronously
     * by the worker thread. This avoids the deadlock that would occur from
     * sending a response synchronously inside the calling thread's
     * transaction lock scope.
     *
     * @param frame Received SRP request stream frame.
     */
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

  private:
    /**
     * @brief Reads bytes from the internal memory map.
     *
     * @param address Start address.
     * @param data Destination buffer.
     * @param size Number of bytes to read.
     */
    void readMemory(uint64_t address, uint8_t* data, uint32_t size);

    /**
     * @brief Writes bytes to the internal memory map.
     *
     * @param address Start address.
     * @param data Source buffer.
     * @param size Number of bytes to write.
     */
    void writeMemory(uint64_t address, const uint8_t* data, uint32_t size);
};

// Convenience
typedef std::shared_ptr<rogue::protocols::srp::SrpV3Server> SrpV3ServerPtr;
}  // namespace srp
}  // namespace protocols
}  // namespace rogue
#endif
