/**
  * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Packetizer Application Interface
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
#ifndef __ROGUE_PROTOCOLS_PACKETIZER_APPLICATION_H__
#define __ROGUE_PROTOCOLS_PACKETIZER_APPLICATION_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>

#include "rogue/Queue.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"

namespace rogue {
namespace protocols {
namespace packetizer {

class Controller;

/**
 * @brief Packetizer application endpoint.
 *
 * @details
 * Provides per-destination stream ingress/egress into the packetizer stack.
 */
class Application : public rogue::interfaces::stream::Master, public rogue::interfaces::stream::Slave {
    //! Core module
    std::shared_ptr<rogue::protocols::packetizer::Controller> cntl_;

    // ID
    uint8_t id_;

    // Transmission thread
    std::thread* thread_;
    bool threadEn_;

    //! Thread background
    void runThread();

    // Application queue
    rogue::Queue<std::shared_ptr<rogue::interfaces::stream::Frame>> queue_;

  public:
    /**
     * @brief Creates a packetizer application endpoint.
     * @param id Destination/application ID.
     * @return Shared pointer to the created application endpoint.
     */
    static std::shared_ptr<rogue::protocols::packetizer::Application> create(uint8_t id);

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Constructs a packetizer application endpoint.
     * @param id Destination/application ID.
     */
    explicit Application(uint8_t id);

    /** @brief Destroys the application endpoint. */
    ~Application();

    /**
     * @brief Attaches the packetizer controller.
     * @param cntl Controller instance that handles packetizer state.
     */
    void setController(std::shared_ptr<rogue::protocols::packetizer::Controller> cntl);

    /**
     * @brief Queues a frame for packetized transmission.
     * @param frame Frame to send through this application channel.
     */
    void pushFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

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
     * @param frame Input frame to packetize.
     */
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);
};

// Convenience
typedef std::shared_ptr<rogue::protocols::packetizer::Application> ApplicationPtr;

}  // namespace packetizer
}  // namespace protocols
};  // namespace rogue

#endif
