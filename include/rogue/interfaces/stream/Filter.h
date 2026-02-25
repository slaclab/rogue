/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    AXI Stream Filter
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
#ifndef __ROGUE_INTERFACES_STREAM_FILTER_H__
#define __ROGUE_INTERFACES_STREAM_FILTER_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>

#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"

namespace rogue {
namespace interfaces {
namespace stream {

/**
 * @brief Stream frame filter by channel and error state.
 *
 * @details
 * Used when frames may carry non-zero channel numbers (for example from data-file
 * readers or batcher splitters). The filter forwards only matching-channel frames
 * and can optionally drop frames marked with errors.
 */
class Filter : public rogue::interfaces::stream::Master, public rogue::interfaces::stream::Slave {
    std::shared_ptr<rogue::Logging> log_;

    // Configurations
    bool dropErrors_;
    uint8_t channel_;

  public:
    /**
     * @brief Creates a stream filter.
     *
     * @param dropErrors Set to `true` to drop frames with error flags.
     * @param channel Channel number to allow through the filter.
     * @return Shared pointer to the created filter.
     */
    static std::shared_ptr<rogue::interfaces::stream::Filter> create(bool dropErrors, uint8_t channel);

    /** @brief Registers this type with Python bindings. */
    static void setup_python();

    /**
     * @brief Constructs a stream filter.
     *
     * @param dropErrors Set to `true` to drop frames with error flags.
     * @param channel Channel number to allow through the filter.
     */
    Filter(bool dropErrors, uint8_t channel);

    /** @brief Destroys the stream filter. */
    ~Filter();

    /**
     * @brief Receives a frame from upstream and applies filter rules.
     *
     * @param frame Frame to evaluate and potentially forward.
     */
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);
};

/** @brief Shared pointer alias for `Filter`. */
typedef std::shared_ptr<rogue::interfaces::stream::Filter> FilterPtr;
}  // namespace stream
}  // namespace interfaces
}  // namespace rogue
#endif
