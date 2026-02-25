/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    Drops frames at a specified rate.
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
#ifndef __ROGUE_INTERFACES_STREAM_RATE_DROP_H__
#define __ROGUE_INTERFACES_STREAM_RATE_DROP_H__
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
 * @brief Stream frame-rate dropper.
 *
 * @details
 * Drops frames at a configured rate, either by frame count or by time period.
 * In period mode, `value` is interpreted as seconds between kept frames.
 * Otherwise, `value` is interpreted as number of dropped frames between kept frames.
 */
class RateDrop : public rogue::interfaces::stream::Master, public rogue::interfaces::stream::Slave {
    // Configurations
    bool periodFlag_;

    uint32_t dropTarget_;

    struct timeval timePeriod_;

    // Status
    uint32_t dropCount_;

    struct timeval nextPeriod_;

  public:
    /**
     * @brief Creates a rate-drop filter.
     *
     * @param period Set to `true` for period mode; `false` for drop-count mode.
     * @param value Period seconds or drop-count setting.
     * @return Shared pointer to the created rate-drop filter.
     */
    static std::shared_ptr<rogue::interfaces::stream::RateDrop> create(bool period, double value);

    /** @brief Registers this type with Python bindings. */
    static void setup_python();

    /**
     * @brief Constructs a rate-drop filter.
     *
     * @param period Set to `true` for period mode; `false` for drop-count mode.
     * @param value Period seconds or drop-count setting.
     */
    RateDrop(bool period, double value);

    /** @brief Destroys the rate-drop filter. */
    ~RateDrop();

    /**
     * @brief Receives a frame and drops/forwards according to configured rate policy.
     *
     * @param frame Incoming frame.
     */
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);
};

/** @brief Shared pointer alias for `RateDrop`. */
typedef std::shared_ptr<rogue::interfaces::stream::RateDrop> RateDropPtr;
}  // namespace stream
}  // namespace interfaces
}  // namespace rogue
#endif
