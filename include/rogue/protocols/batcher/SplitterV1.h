/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    SLAC AXI Splitter V1
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
#ifndef __ROGUE_PROTOCOLS_BATCHER_SPLITTER_V1_H__
#define __ROGUE_PROTOCOLS_BATCHER_SPLITTER_V1_H__
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
 * @brief Splits one batcher v1 super-frame into per-record output frames.
 *
 * @details
 * Protocol reference: https://confluence.slac.stanford.edu/x/th1SDg
 *
 * `SplitterV1` uses `CoreV1` to parse a batcher super-frame, then emits one
 * Rogue stream frame per parsed `Data` record:
 * - Payload bytes copied from record data.
 * - Channel set from record destination.
 * - First/last user fields propagated from record metadata.
 *
 * Threading model:
 * - No internal worker thread is created.
 * - Processing executes synchronously in the caller thread of `acceptFrame()`.
 */
class SplitterV1 : public rogue::interfaces::stream::Master, public rogue::interfaces::stream::Slave {
  public:
    /**
     * @brief Creates a `SplitterV1` instance.
     * @return Shared pointer to the created splitter.
     */
    static std::shared_ptr<rogue::protocols::batcher::SplitterV1> create();

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /** @brief Constructs a `SplitterV1` instance. */
    SplitterV1();

    /** @brief Destroys the splitter. */
    ~SplitterV1();

    /**
     * @brief Accepts one batcher v1 frame and emits parsed records as frames.
     * @param frame Input batcher super-frame.
     */
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);
};

// Convienence
typedef std::shared_ptr<rogue::protocols::batcher::SplitterV1> SplitterV1Ptr;
}  // namespace batcher
}  // namespace protocols
}  // namespace rogue
#endif
