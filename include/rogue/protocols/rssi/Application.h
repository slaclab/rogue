/**
  * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * RSSI Application
 * ----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to
 * the license terms in the LICENSE.txt file found in the top-level directory
 * of this distribution and at:
 *    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
 * No part of the rogue software platform, including this file, may be
 * copied, modified, propagated, or distributed except according to the terms
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
 **/
#ifndef __ROGUE_PROTOCOLS_RSSI_APPLICATION_H__
#define __ROGUE_PROTOCOLS_RSSI_APPLICATION_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>

#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"

namespace rogue {
namespace protocols {
namespace rssi {

class Controller;

/**
 * @brief RSSI application-side endpoint.
 *
 * @details
 * Provides stream ingress/egress for payload traffic through the RSSI stack.
 */
class Application : public rogue::interfaces::stream::Master, public rogue::interfaces::stream::Slave {
    //! Core module
    std::shared_ptr<rogue::protocols::rssi::Controller> cntl_;

    // Transmission thread
    std::thread* thread_;
    bool threadEn_;

    //! Thread background
    void runThread();

  public:
    /**
     * @brief Creates an RSSI application endpoint.
     * @return Shared pointer to the created application endpoint.
     */
    static std::shared_ptr<rogue::protocols::rssi::Application> create();

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /** @brief Constructs an RSSI application endpoint. */
    Application();

    /** @brief Destroys the application endpoint. */
    ~Application();

    /**
     * @brief Attaches the RSSI controller.
     * @param cntl Controller instance that owns protocol state.
     */
    void setController(std::shared_ptr<rogue::protocols::rssi::Controller> cntl);

    /**
     * @brief Allocates a frame for upstream writers.
     *
     * @details
     * Called by the stream master side of this endpoint.
     *
     * @param size Minimum requested payload size in bytes.
     * @param zeroCopyEn True to allow zero-copy allocation when possible.
     * @return Newly allocated frame.
     */
    std::shared_ptr<rogue::interfaces::stream::Frame> acceptReq(uint32_t size, bool zeroCopyEn);

    /**
     * @brief Accepts a frame from upstream application logic.
     * @param frame Input frame for RSSI transmission.
     */
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);
};

// Convienence
typedef std::shared_ptr<rogue::protocols::rssi::Application> ApplicationPtr;

}  // namespace rssi
}  // namespace protocols
};  // namespace rogue

#endif
