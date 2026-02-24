/**
  * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Packetizer Transport
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
#ifndef __ROGUE_PROTOCOLS_PACKETIZER_TRANSPORT_H__
#define __ROGUE_PROTOCOLS_PACKETIZER_TRANSPORT_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>

#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"

namespace rogue {
namespace protocols {
namespace packetizer {

class Controller;

/**
 * @brief Packetizer transport endpoint.
 *
 * @details
 * Bridges raw stream traffic to/from the packetizer controller.
 */
class Transport : public rogue::interfaces::stream::Master, public rogue::interfaces::stream::Slave {
    //! Core module
    std::shared_ptr<rogue::protocols::packetizer::Controller> cntl_;

    // Transmission thread
    std::thread* thread_;
    bool threadEn_;

    //! Thread background
    void runThread();

  public:
    /**
     * @brief Creates a packetizer transport endpoint.
     * @return Shared pointer to the created transport endpoint.
     */
    static std::shared_ptr<rogue::protocols::packetizer::Transport> create();

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /** @brief Constructs a packetizer transport endpoint. */
    Transport();

    /** @brief Destroys the packetizer transport endpoint. */
    ~Transport();

    /**
     * @brief Attaches the packetizer controller.
     * @param cntl Controller instance that handles packetizer protocol processing.
     */
    void setController(std::shared_ptr<rogue::protocols::packetizer::Controller> cntl);

    /**
     * @brief Accepts a frame from the upstream stream interface.
     * @param frame Input frame to decode and forward to controller logic.
     */
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);
};

// Convenience
typedef std::shared_ptr<rogue::protocols::packetizer::Transport> TransportPtr;

}  // namespace packetizer
}  // namespace protocols
};  // namespace rogue

#endif
