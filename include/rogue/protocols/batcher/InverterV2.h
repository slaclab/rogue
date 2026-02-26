/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *   SLAC AXI Inverter V2
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
#ifndef __ROGUE_PROTOCOLS_BATCHER_INVERTER_V2_H__
#define __ROGUE_PROTOCOLS_BATCHER_INVERTER_V2_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <thread>

#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"

namespace rogue {
namespace protocols {
namespace batcher {

/**
 * @brief In-place inverter for SLAC AXI Batcher v2 framing.
 *
 * @details
 * Protocol reference: https://confluence.slac.stanford.edu/x/L2VlK
 *
 * `InverterV2` uses `CoreV2` metadata to reinterpret/shift record tail data
 * inside the original frame payload. This produces a transformed frame layout
 * expected by downstream consumers without allocating one frame per record.
 * It is not a batching or unbatching stage: one input frame yields one output
 * frame after in-place reformatting.
 *
 * `InverterV2` transforms a batcher v2 frame by copying per-record tail fields
 * into the header/tail positions expected by downstream consumers and trimming
 * the final tail from payload. The transformed frame is then forwarded.
 * Use `SplitterV2` when true unbatching (one output frame per record) is
 * desired.
 *
 * Threading model:
 * - No internal worker thread is created.
 * - Processing executes synchronously in the caller thread of `acceptFrame()`.
 */
class InverterV2 : public rogue::interfaces::stream::Master, public rogue::interfaces::stream::Slave {
  public:
    /**
     * @brief Creates an `InverterV2` instance.
     * @return Shared pointer to the created inverter.
     */
    static std::shared_ptr<rogue::protocols::batcher::InverterV2> create();

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /** @brief Constructs an `InverterV2` instance. */
    InverterV2();

    /** @brief Destroys the inverter. */
    ~InverterV2();

    /**
     * @brief Accepts, transforms, and forwards one batcher v2 frame.
     * @param frame Input frame to transform.
     */
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);
};

// Convienence
typedef std::shared_ptr<rogue::protocols::batcher::InverterV2> InverterV2Ptr;
}  // namespace batcher
}  // namespace protocols
}  // namespace rogue
#endif
