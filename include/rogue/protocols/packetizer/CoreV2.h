/**
  * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Packetizer Core, Version 2
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
#ifndef __ROGUE_PROTOCOLS_PACKETIZER_CORE_V2_H__
#define __ROGUE_PROTOCOLS_PACKETIZER_CORE_V2_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <thread>

namespace rogue {
namespace protocols {
namespace packetizer {

class Transport;
class Application;
class ControllerV2;

/**
 * @brief Packetizer v2 core wiring object.
 *
 * @details
 * Owns and connects transport, v2 controller, and per-destination application
 * endpoints for the packetizer v2 stack.
 */
class CoreV2 {
    //! Transport module
    std::shared_ptr<rogue::protocols::packetizer::Transport> tran_;

    //! Application modules
    std::shared_ptr<rogue::protocols::packetizer::Application> app_[256];

    //! Core module
    std::shared_ptr<rogue::protocols::packetizer::ControllerV2> cntl_;

  public:
    /**
     * @brief Creates a packetizer v2 core.
     * @param enIbCrc Enable inbound CRC checking.
     * @param enObCrc Enable outbound CRC generation.
     * @param enSsi Enable SSI framing behavior.
     * @return Shared pointer to the created packetizer v2 core.
     */
    static std::shared_ptr<rogue::protocols::packetizer::CoreV2> create(bool enIbCrc, bool enObCrc, bool enSsi);

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Constructs a packetizer v2 core.
     * @param enIbCrc Enable inbound CRC checking.
     * @param enObCrc Enable outbound CRC generation.
     * @param enSsi Enable SSI framing behavior.
     */
    CoreV2(bool enIbCrc, bool enObCrc, bool enSsi);

    /** @brief Destroys the packetizer v2 core. */
    ~CoreV2();

    /**
     * @brief Returns the transport-facing endpoint.
     * @return Shared transport interface.
     */
    std::shared_ptr<rogue::protocols::packetizer::Transport> transport();

    /**
     * @brief Returns an application endpoint by destination ID.
     * @param dest Destination channel ID.
     * @return Shared application endpoint.
     */
    std::shared_ptr<rogue::protocols::packetizer::Application> application(uint8_t dest);

    /**
     * @brief Returns total dropped-frame count reported by the controller.
     * @return Number of dropped frames.
     */
    uint32_t getDropCount();

    /**
     * @brief Sets transmit timeout for internal controller operations.
     * @param timeout Timeout in microseconds.
     */
    void setTimeout(uint32_t timeout);
};

// Convenience
typedef std::shared_ptr<rogue::protocols::packetizer::CoreV2> CoreV2Ptr;

}  // namespace packetizer
}  // namespace protocols
};  // namespace rogue

#endif
