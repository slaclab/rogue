/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    AXI Stream FIFO
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
#ifndef __ROGUE_INTERFACES_STREAM_FIFO_H__
#define __ROGUE_INTERFACES_STREAM_FIFO_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <thread>

#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"

namespace rogue {
namespace interfaces {
namespace stream {

/**
 * @brief Stream frame FIFO.
 *
 * @details
 * Buffers incoming frames and forwards them to downstream slaves from a worker thread.
 * For each accepted frame:
 * - If `noCopy` is `true`, the original frame object is queued (no payload copy, no trim).
 * - If `noCopy` is `false`, a new frame is allocated and payload bytes are copied.
 * - In copy mode, `trimSize` can cap copied payload length.
 *
 * Queue backpressure/drop behavior is controlled by `maxDepth`:
 * - `maxDepth > 0`: once queue depth reaches `maxDepth`, new incoming frames are dropped.
 * - `maxDepth == 0`: no busy/drop threshold is applied by this FIFO (queue can continue growing).
 *
 * Trim behavior:
 * - `trimSize > 0` and `noCopy == false`: copied payload is limited to `min(payload, trimSize)`.
 * - `trimSize == 0`: copied payload is not trimmed.
 * - `noCopy == true`: `trimSize` is ignored.
 */
class Fifo : public rogue::interfaces::stream::Master, public rogue::interfaces::stream::Slave {
    std::shared_ptr<rogue::Logging> log_;

    // Configurations
    uint32_t maxDepth_;
    uint32_t trimSize_;
    bool noCopy_;

    // Drop frame counter
    std::size_t dropFrameCnt_;

    // Queue
    rogue::Queue<std::shared_ptr<rogue::interfaces::stream::Frame>> queue_;

    // Transmission thread
    bool threadEn_;
    std::thread* thread_;

    // Thread background
    void runThread();

  public:
    /**
     * @brief Creates a FIFO stream buffer.
     *
     * @details Exposed as `rogue.interfaces.stream.Fifo()` in Python.
     *
     * @param maxDepth Queue busy/drop threshold in frames. `0` disables threshold-based drops.
     * @param trimSize Payload trim limit in copy mode. `0` disables trimming.
     * @param noCopy Set to `true` to queue original frames; when `true`, `trimSize` is ignored.
     * @return Shared pointer to the created FIFO.
     */
    static std::shared_ptr<rogue::interfaces::stream::Fifo> create(uint32_t maxDepth, uint32_t trimSize, bool noCopy);

    /** @brief Registers this type with Python bindings. */
    static void setup_python();

    /**
     * @brief Constructs a FIFO stream buffer.
     *
     * @param maxDepth Queue busy/drop threshold in frames. `0` disables threshold-based drops.
     * @param trimSize Payload trim limit in copy mode. `0` disables trimming.
     * @param noCopy Set to `true` to queue original frames; when `true`, `trimSize` is ignored.
     */
    Fifo(uint32_t maxDepth, uint32_t trimSize, bool noCopy);

    /** @brief Destroys the FIFO and stops internal worker thread. */
    ~Fifo();

    /** @brief Returns current FIFO queue depth. */
    std::size_t size();

    /** @brief Returns the total dropped-frame counter. */
    std::size_t dropCnt() const;

    /** @brief Clears FIFO counters (including dropped-frame count). */
    void clearCnt();

    /**
     * @brief Receives a frame from upstream and enqueues or drops it.
     *
     * @param frame Incoming frame.
     */
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);
};

/** @brief Shared pointer alias for `Fifo`. */
typedef std::shared_ptr<rogue::interfaces::stream::Fifo> FifoPtr;
}  // namespace stream
}  // namespace interfaces
}  // namespace rogue
#endif
