/**
  * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Packetizer Controller
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
#ifndef __ROGUE_PROTOCOLS_PACKETIZER_CONTROLLER_H__
#define __ROGUE_PROTOCOLS_PACKETIZER_CONTROLLER_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <atomic>
#include <memory>

#include "rogue/Logging.h"
#include "rogue/Queue.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"

namespace rogue {
namespace protocols {
namespace packetizer {

class Application;
class Transport;
class Header;

/**
 * @brief Packetizer base controller.
 *
 * @details
 * Shared controller logic for packetizer variants that route data between
 * one transport endpoint and multiple application endpoints.
 */
class Controller {
  protected:
    // parameters
    bool enSsi_;
    uint32_t appIndex_;
    uint32_t tranIndex_;
    bool transSof_[256];
    uint32_t tranCount_[256];
    uint32_t crc_[256];
    uint8_t tranDest_;
    std::atomic<uint32_t> dropCount_;
    uint32_t headSize_;
    uint32_t tailSize_;
    uint32_t alignSize_;

    struct timeval timeout_;

    std::shared_ptr<rogue::Logging> log_;

    std::shared_ptr<rogue::interfaces::stream::Frame> tranFrame_[256];

    std::mutex appMtx_;
    std::mutex tranMtx_;

    std::shared_ptr<rogue::protocols::packetizer::Transport> tran_;
    std::shared_ptr<rogue::protocols::packetizer::Application>* app_;

    rogue::Queue<std::shared_ptr<rogue::interfaces::stream::Frame>> tranQueue_;

  public:
    /**
     * @brief Constructs a packetizer controller base.
     * @param tran Transport endpoint associated with this controller.
     * @param app Pointer to application endpoint array indexed by destination.
     * @param headSize Header bytes inserted per packet.
     * @param tailSize Trailer bytes inserted per packet.
     * @param alignSize Payload alignment requirement in bytes.
     * @param enSsi Enable SSI framing behavior.
     */
    Controller(std::shared_ptr<rogue::protocols::packetizer::Transport> tran,
               std::shared_ptr<rogue::protocols::packetizer::Application>* app,
               uint32_t headSize,
               uint32_t tailSize,
               uint32_t alignSize,
               bool enSsi);

    /** @brief Destroys the packetizer controller base. */
    ~Controller();

    /**
     * @brief Allocates a transport-path frame.
     * @param size Minimum payload size in bytes.
     * @return Allocated frame.
     */
    std::shared_ptr<rogue::interfaces::stream::Frame> reqFrame(uint32_t size);

    /**
     * @brief Processes a frame received from transport.
     * @param frame Input transport frame.
     */
    virtual void transportRx(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    /** @brief Stops the internal transmit queue. */
    void stopQueue();

    /** @brief Stops controller processing. */
    void stop();

    /**
     * @brief Returns the next frame for transport transmission.
     * @return Frame ready for transport transmit, or null when none is available.
     */
    std::shared_ptr<rogue::interfaces::stream::Frame> transportTx();

    /**
     * @brief Processes a frame received from an application endpoint.
     * @param frame Input application frame.
     * @param id Application destination identifier.
     */
    virtual void applicationRx(std::shared_ptr<rogue::interfaces::stream::Frame> frame, uint8_t id);

    /**
     * @brief Returns dropped-frame counter.
     * @return Number of dropped frames.
     */
    uint32_t getDropCount();

    /**
     * @brief Sets timeout in microseconds for frame transmits.
     * @param timeout Timeout value in microseconds.
     */
    void setTimeout(uint32_t timeout);
};

// Convenience
typedef std::shared_ptr<rogue::protocols::packetizer::Controller> ControllerPtr;

}  // namespace packetizer
}  // namespace protocols
};  // namespace rogue

#endif
