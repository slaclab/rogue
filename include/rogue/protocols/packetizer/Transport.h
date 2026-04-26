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

#include <atomic>
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
 *
 * Threading model:
 * - Inbound frames are handled synchronously by `acceptFrame()`, which forwards
 *   each frame to `Controller::transportRx()`.
 * - Outbound frames are produced by a dedicated background thread started in
 *   `setController()`. That thread drains `Controller::transportTx()` and
 *   forwards returned frames via `sendFrame()`.
 *
 * Lifetime contract:
 * - `setController()` must be called before destruction so the TX queue thread
 *   can be started/stopped against a valid controller.
 */
class Transport : public rogue::interfaces::stream::Master, public rogue::interfaces::stream::Slave {
    // Packetizer controller endpoint.
    std::shared_ptr<rogue::protocols::packetizer::Controller> cntl_;

  protected:
    // Default-init: dtor before setController() must be a no-op.
    // threadEn_ is atomic to close the stop()/runThread() teardown race.
    std::thread* thread_ = nullptr;
    std::atomic<bool> threadEn_{false};

  private:
    // Worker thread entry point.
    void runThread();

  public:
    /**
     * @brief Creates a packetizer transport endpoint.
     *
     * @details
     * This static factory is the preferred construction path when the object
     * is shared across Rogue graph connections or exposed to Python.
     * It returns `std::shared_ptr` ownership compatible with Rogue pointer typedefs.
     *
     * @return Shared pointer to the created transport endpoint.
     */
    static std::shared_ptr<rogue::protocols::packetizer::Transport> create();

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Constructs a packetizer transport endpoint.
     *
     * @details
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` when shared ownership or Python exposure is required.
     */
    Transport();

    /** @brief Destroys the packetizer transport endpoint. */
    ~Transport();

    /**
     * @brief Attaches the packetizer controller.
     *
     * @details
     * Stores the controller reference and starts the outbound worker thread
     * that forwards controller-generated transport frames.
     *
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
