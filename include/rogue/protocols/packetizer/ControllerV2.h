/**
  * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Packetizer Controller, Version 2
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
#ifndef __ROGUE_PROTOCOLS_PACKETIZER_CONTROLLER_V2_H__
#define __ROGUE_PROTOCOLS_PACKETIZER_CONTROLLER_V2_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>

#include "rogue/EnableSharedFromThis.h"
#include "rogue/Logging.h"
#include "rogue/Queue.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/protocols/packetizer/Controller.h"

namespace rogue {
namespace protocols {
namespace packetizer {

class Application;
class Transport;
class Header;

/**
 * @brief Packetizer controller implementation for protocol v2.
 *
 * @details
 * Handles packet segmentation/reassembly and optional CRC processing between
 * transport and application endpoints.
 */
class ControllerV2 : public Controller, public rogue::EnableSharedFromThis<rogue::protocols::packetizer::ControllerV2> {
    bool enIbCrc_;
    bool enObCrc_;

  public:
    /**
     * @brief Creates a packetizer v2 controller.
     * @param enIbCrc Enable inbound CRC verification.
     * @param enObCrc Enable outbound CRC generation.
     * @param enSsi Enable SSI framing behavior.
     * @param tran Transport endpoint attached to this controller.
     * @param app Pointer to array of application endpoints indexed by destination.
     * @return Shared pointer to a new controller instance.
     */
    static std::shared_ptr<rogue::protocols::packetizer::ControllerV2> create(
        bool enIbCrc,
        bool enObCrc,
        bool enSsi,
        std::shared_ptr<rogue::protocols::packetizer::Transport> tran,
        std::shared_ptr<rogue::protocols::packetizer::Application>* app);

    /**
     * @brief Constructs a packetizer v2 controller.
     * @param enIbCrc Enable inbound CRC verification.
     * @param enObCrc Enable outbound CRC generation.
     * @param enSsi Enable SSI framing behavior.
     * @param tran Transport endpoint attached to this controller.
     * @param app Pointer to array of application endpoints indexed by destination.
     */
    ControllerV2(bool enIbCrc,
                 bool enObCrc,
                 bool enSsi,
                 std::shared_ptr<rogue::protocols::packetizer::Transport> tran,
                 std::shared_ptr<rogue::protocols::packetizer::Application>* app);

    /** @brief Destroys the controller instance. */
    ~ControllerV2();

    /**
     * @brief Processes a frame received at the transport interface.
     * @param frame Transport frame to decode and route.
     */
    void transportRx(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    /**
     * @brief Processes a frame received from one application endpoint.
     * @param frame Application frame to packetize.
     * @param id Application/destination identifier.
     */
    void applicationRx(std::shared_ptr<rogue::interfaces::stream::Frame> frame, uint8_t id);
};

// Convenience
typedef std::shared_ptr<rogue::protocols::packetizer::ControllerV2> ControllerV2Ptr;

}  // namespace packetizer
}  // namespace protocols
};  // namespace rogue

#endif
