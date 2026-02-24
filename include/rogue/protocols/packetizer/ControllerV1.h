/**
  * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Packetizer Controller, Version 1
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
#ifndef __ROGUE_PROTOCOLS_PACKETIZER_CONTROLLER_V1_H__
#define __ROGUE_PROTOCOLS_PACKETIZER_CONTROLLER_V1_H__
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

/** Packetizer controller implementation for protocol v1. */
class ControllerV1 : public Controller, public rogue::EnableSharedFromThis<rogue::protocols::packetizer::ControllerV1> {
  public:
    /**
     * Create a packetizer v1 controller.
     * @param[in] enSsi Enable SSI framing behavior.
     *  @param[in] tran Transport endpoint attached to this controller.
     *  @param[in] app Pointer to array of application endpoints indexed by destination.
     *  @return Shared pointer to a new controller instance.
     */
    static std::shared_ptr<rogue::protocols::packetizer::ControllerV1> create(
        bool enSsi,
        std::shared_ptr<rogue::protocols::packetizer::Transport> tran,
        std::shared_ptr<rogue::protocols::packetizer::Application>* app);

    /**
     * Construct a packetizer v1 controller.
     * @param[in] enSsi Enable SSI framing behavior.
     *  @param[in] tran Transport endpoint attached to this controller.
     *  @param[in] app Pointer to array of application endpoints indexed by destination.
     */
    ControllerV1(bool enSsi,
                 std::shared_ptr<rogue::protocols::packetizer::Transport> tran,
                 std::shared_ptr<rogue::protocols::packetizer::Application>* app);

    //! Destructor
    ~ControllerV1();

    //! Frame received at transport interface
    void transportRx(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    /**
     * Process a frame received from one application endpoint.
     * @param[in] frame Application frame to packetize.
     *  @param[in] id Application/destination identifier.
     */
    void applicationRx(std::shared_ptr<rogue::interfaces::stream::Frame> frame, uint8_t id);
};

// Convenience
typedef std::shared_ptr<rogue::protocols::packetizer::ControllerV1> ControllerV1Ptr;

}  // namespace packetizer
}  // namespace protocols
};  // namespace rogue

#endif
