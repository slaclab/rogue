/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    SLAC AXI Batcher V1 Combiner (SW Batcher)
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
#ifndef __ROGUE_PROTOCOLS_BATCHER_COMBINER_V1_H__
#define __ROGUE_PROTOCOLS_BATCHER_COMBINER_V1_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <mutex>
#include <vector>

#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"

namespace rogue {
namespace protocols {
namespace batcher {

/**
 * @brief Combines individual frames into a batcher v1 super-frame.
 *
 * @details
 * Protocol reference: https://confluence.slac.stanford.edu/x/th1SDg
 *
 * `CombinerV1` is the software inverse of `SplitterV1`. It collects
 * individual Rogue stream frames and packs them into a single batcher
 * v1 super-frame with the appropriate super-header and per-record tails.
 *
 * The `width` parameter controls the AXI stream width encoding:
 * - 0 = 16-bit  (header=2, tail=8)
 * - 1 = 32-bit  (header=4, tail=8)
 * - 2 = 64-bit  (header=8, tail=8)
 * - 3 = 128-bit (header=16, tail=16)
 * - 4 = 256-bit (header=32, tail=32)
 * - 5 = 512-bit (header=64, tail=64)
 *
 * Threading model:
 * - No internal worker thread is created.
 * - `acceptFrame()` queues frames; `sendBatch()` builds and emits the super-frame.
 */
class CombinerV1 : public rogue::interfaces::stream::Master, public rogue::interfaces::stream::Slave {
    std::shared_ptr<rogue::Logging> log_;

    // Queued frames waiting to be batched.
    std::vector<std::shared_ptr<rogue::interfaces::stream::Frame> > queue_;

    // Width encoding (0-5).
    uint8_t width_;

    // Header size in bytes.
    uint32_t headerSize_;

    // Tail size in bytes.
    uint32_t tailSize_;

    // Sequence counter.
    uint8_t seq_;

    // Mutex for queue access.
    std::mutex mtx_;

  public:
    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Creates a `CombinerV1` instance.
     * @param width AXI stream width encoding (0-5).
     * @return Shared pointer to the created combiner.
     */
    static std::shared_ptr<rogue::protocols::batcher::CombinerV1> create(uint8_t width);

    /**
     * @brief Constructs a `CombinerV1` instance.
     * @param width AXI stream width encoding (0-5).
     */
    explicit CombinerV1(uint8_t width);

    /** @brief Destroys the combiner. */
    ~CombinerV1();

    /**
     * @brief Accepts a frame and immediately queues it for batching.
     * @param frame Input frame to be included in the next batch.
     */
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    /**
     * @brief Builds and sends a batcher v1 super-frame from all queued frames.
     *
     * @details
     * If no frames are queued, this is a no-op. After sending, the queue
     * is cleared and the sequence counter is incremented.
     */
    void sendBatch();

    /**
     * @brief Returns the number of frames currently queued.
     * @return Queue depth.
     */
    uint32_t getCount();
};

// Convenience
typedef std::shared_ptr<rogue::protocols::batcher::CombinerV1> CombinerV1Ptr;
}  // namespace batcher
}  // namespace protocols
}  // namespace rogue
#endif
