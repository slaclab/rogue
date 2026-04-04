/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    SLAC AXI Batcher V2 Combiner (SW Batcher)
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
#ifndef __ROGUE_PROTOCOLS_BATCHER_COMBINER_V2_H__
#define __ROGUE_PROTOCOLS_BATCHER_COMBINER_V2_H__
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
 * @brief Combines individual frames into a batcher v2 super-frame.
 *
 * @details
 * Protocol reference: https://confluence.slac.stanford.edu/x/L2VlK
 *
 * `CombinerV2` is the software inverse of `SplitterV2`. It collects
 * individual Rogue stream frames and packs them into a single batcher
 * v2 super-frame with a 2-byte super-header and 7-byte per-record tails.
 *
 * Threading model:
 * - No internal worker thread is created.
 * - `push()` queues frames; `sendBatch()` builds and emits the super-frame.
 */
class CombinerV2 : public rogue::interfaces::stream::Master, public rogue::interfaces::stream::Slave {
    std::shared_ptr<rogue::Logging> log_;

    // Queued frames waiting to be batched.
    std::vector<std::shared_ptr<rogue::interfaces::stream::Frame> > queue_;

    // Sequence counter.
    uint8_t seq_;

    // Mutex for queue access.
    std::mutex mtx_;

  public:
    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Creates a `CombinerV2` instance.
     * @return Shared pointer to the created combiner.
     */
    static std::shared_ptr<rogue::protocols::batcher::CombinerV2> create();

    /**
     * @brief Constructs a `CombinerV2` instance.
     */
    CombinerV2();

    /** @brief Destroys the combiner. */
    ~CombinerV2();

    /**
     * @brief Accepts a frame and immediately queues it for batching.
     * @param frame Input frame to be included in the next batch.
     */
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    /**
     * @brief Builds and sends a batcher v2 super-frame from all queued frames.
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
typedef std::shared_ptr<rogue::protocols::batcher::CombinerV2> CombinerV2Ptr;
}  // namespace batcher
}  // namespace protocols
}  // namespace rogue
#endif
