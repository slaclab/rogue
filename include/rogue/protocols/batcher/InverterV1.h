/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *   SLAC AXI Inverter V1
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
#ifndef __ROGUE_PROTOCOLS_BATCHER_INVERTER_V1_H__
#define __ROGUE_PROTOCOLS_BATCHER_INVERTER_V1_H__
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
 * @brief In-place inverter for SLAC AXI Batcher v1 framing.
 *
 * @details
 * Protocol reference: https://confluence.slac.stanford.edu/x/th1SDg
 *
 * `InverterV1` uses `CoreV1` metadata to reinterpret/shift record tail data
 * inside the original frame payload. This produces a transformed frame layout
 * expected by downstream consumers without allocating one frame per record.
 * It is not a batching or unbatching stage: one input frame yields one output
 * frame after in-place reformatting.
 *
 * `InverterV1` transforms a batcher v1 frame by copying per-record tail fields
 * into the header/tail positions expected by downstream consumers and trimming
 * the final tail from payload. The transformed frame is then forwarded.
 * Use `SplitterV1` when true unbatching (one output frame per record) is
 * desired.
 *
 * Threading model:
 * - No internal worker thread is created.
 * - Processing executes synchronously in the caller thread of `acceptFrame()`.
 */
class InverterV1 : public rogue::interfaces::stream::Master, public rogue::interfaces::stream::Slave {
  public:
    /**
     * @brief Creates an `InverterV1` instance.
     * @return Shared pointer to the created inverter.
     */
    static std::shared_ptr<rogue::protocols::batcher::InverterV1> create();

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /** @brief Constructs an `InverterV1` instance. */
    InverterV1();

    /** @brief Destroys the inverter. */
    ~InverterV1();

    /**
     * @brief Accepts, transforms, and forwards one batcher v1 frame.
     * @param frame Input frame to transform.
     */
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);
};

// Convienence
typedef std::shared_ptr<rogue::protocols::batcher::InverterV1> InverterV1Ptr;
}  // namespace batcher
}  // namespace protocols
}  // namespace rogue
#endif
