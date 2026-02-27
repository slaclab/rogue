/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    SLAC AXI Splitter V2
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
#ifndef __ROGUE_PROTOCOLS_BATCHER_SPLITTER_V2_H__
#define __ROGUE_PROTOCOLS_BATCHER_SPLITTER_V2_H__
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
 * @brief Splits one batcher v2 super-frame into per-record output frames.
 *
 * @details
 * Protocol reference: https://confluence.slac.stanford.edu/x/L2VlK
 *
 * `SplitterV2` uses `CoreV2` to parse a batcher super-frame, then emits one
 * Rogue stream frame per parsed `Data` record:
 * - Payload bytes copied from record data.
 * - Channel set from record destination.
 * - First/last user fields propagated from record metadata.
 *
 * Threading model:
 * - No internal worker thread is created.
 * - Processing executes synchronously in the caller thread of `acceptFrame()`.
 */
class SplitterV2 : public rogue::interfaces::stream::Master, public rogue::interfaces::stream::Slave {
  public:
    /**
     * @brief Creates a `SplitterV2` instance.
     *
     * @details
     * This static factory is the preferred construction path when the object
     * is shared across Rogue graph connections or exposed to Python.
     * It returns `std::shared_ptr` ownership compatible with Rogue pointer typedefs.
     *
     * @return Shared pointer to the created splitter.
     */
    static std::shared_ptr<rogue::protocols::batcher::SplitterV2> create();

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Constructs a `SplitterV2` instance.
     *
     * @details
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` when shared ownership or Python exposure is required.
     */
    SplitterV2();

    /** @brief Destroys the splitter. */
    ~SplitterV2();

    /**
     * @brief Accepts one batcher v2 frame and emits parsed records as frames.
     * @param frame Input batcher super-frame.
     */
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);
};

// Convienence
typedef std::shared_ptr<rogue::protocols::batcher::SplitterV2> SplitterV2Ptr;
}  // namespace batcher
}  // namespace protocols
}  // namespace rogue
#endif
