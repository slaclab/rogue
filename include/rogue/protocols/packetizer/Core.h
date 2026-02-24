/**
  * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Packetizer Core
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
#ifndef __ROGUE_PROTOCOLS_PACKETIZER_CORE_H__
#define __ROGUE_PROTOCOLS_PACKETIZER_CORE_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <thread>

namespace rogue {
namespace protocols {
namespace packetizer {

class Transport;
class Application;
class Controller;

/**
 * @brief Packetizer core wiring object.
 * Owns and connects transport, controller, and per-destination application
 *  endpoints for the packetizer v1 stack.
 */
class Core {
    //! Transport module
    std::shared_ptr<rogue::protocols::packetizer::Transport> tran_;

    //! Application modules
    std::shared_ptr<rogue::protocols::packetizer::Application> app_[256];

    //! Core module
    std::shared_ptr<rogue::protocols::packetizer::Controller> cntl_;

  public:
    //! Class creation
    static std::shared_ptr<rogue::protocols::packetizer::Core> create(bool enSsi);

    //! Setup class in python
    static void setup_python();

    //! Creator
    explicit Core(bool enSsi);

    /**
     * Destroy the packetizer core. */
     *     ~Core();
     *
     *     /** Return the transport-facing endpoint.
     * @return Shared transport interface.
     */
    std::shared_ptr<rogue::protocols::packetizer::Transport> transport();

    /**
     * Return an application endpoint by destination ID.
     * @param[in] dest Destination channel ID.
     *  @return Shared application endpoint.
     */
    std::shared_ptr<rogue::protocols::packetizer::Application> application(uint8_t dest);

    /**
     * Return total dropped-frame count reported by the controller.
     * @return Number of dropped frames.
     */
    uint32_t getDropCount();

    /**
     * Set transmit timeout for internal controller operations.
     * @param[in] timeout Timeout in microseconds.
     */
    void setTimeout(uint32_t timeout);
};

// Convenience
typedef std::shared_ptr<rogue::protocols::packetizer::Core> CorePtr;

}  // namespace packetizer
}  // namespace protocols
};  // namespace rogue

#endif
