/**
  * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * RSSI Transport
 * ----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to
 * the license terms in the LICENSE.txt file found in the top-level directory
 * of this distribution and at:
 *  https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
 * No part of the rogue software platform, including this file, may be
 * copied, modified, propagated, or distributed except according to the terms
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
 **/
#ifndef __ROGUE_PROTOCOLS_RSSI_TRANSPORT_H__
#define __ROGUE_PROTOCOLS_RSSI_TRANSPORT_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>

#include "rogue/Queue.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"

namespace rogue {
namespace protocols {
namespace rssi {

class Controller;

/**
 * @brief RSSI transport endpoint.
 *
 * @details
 * Bridges stream traffic between the RSSI controller and the underlying link.
 */
class Transport : public rogue::interfaces::stream::Master, public rogue::interfaces::stream::Slave {
    //! Core module
    std::shared_ptr<rogue::protocols::rssi::Controller> cntl_;

  public:
    /**
     * @brief Creates a new transport endpoint instance.
     * @return Shared pointer to the created transport endpoint.
     */
    static std::shared_ptr<rogue::protocols::rssi::Transport> create();

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /** @brief Constructs a transport endpoint. */
    Transport();

    /** @brief Destroys the transport endpoint. */
    ~Transport();

    /**
     * @brief Attaches the RSSI controller.
     * @param cntl Controller instance that owns protocol state.
     */
    void setController(std::shared_ptr<rogue::protocols::rssi::Controller> cntl);

    /**
     * @brief Accepts a frame from the upstream stream interface.
     * @param frame Input frame to decode and forward to controller logic.
     */
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);
};

// Convienence
typedef std::shared_ptr<rogue::protocols::rssi::Transport> TransportPtr;

}  // namespace rssi
}  // namespace protocols
};  // namespace rogue

#endif
