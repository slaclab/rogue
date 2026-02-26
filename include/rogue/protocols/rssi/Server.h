/**
  * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 *      RSSI Server Class
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
#ifndef __ROGUE_PROTOCOLS_RSSI_SERVER_H__
#define __ROGUE_PROTOCOLS_RSSI_SERVER_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <thread>

namespace rogue {
namespace protocols {
namespace rssi {

class Transport;
class Application;
class Controller;

/**
 * @brief RSSI server convenience wrapper.
 *
 * @details
 * Bundles transport, application, and controller components for server-side
 * RSSI links.
 * Protocol reference: https://confluence.slac.stanford.edu/x/1IyfD
 *
 * Construction wires the internal components together:
 * `Transport <-> Controller <-> Application`.
 */
class Server {
    // Transport endpoint.
    std::shared_ptr<rogue::protocols::rssi::Transport> tran_;

    // Application endpoint.
    std::shared_ptr<rogue::protocols::rssi::Application> app_;

    // Protocol controller.
    std::shared_ptr<rogue::protocols::rssi::Controller> cntl_;

  public:
    /**
     * @brief Creates an RSSI server bundle.
     * @param segSize Initial local maximum segment size.
     * @return Shared pointer to the created server bundle.
     */
    static std::shared_ptr<rogue::protocols::rssi::Server> create(uint32_t segSize);

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Constructs an RSSI server bundle.
     * @param segSize Initial local maximum segment size.
     */
    explicit Server(uint32_t segSize);

    /** @brief Destroys the server bundle. */
    ~Server();

    /**
     * @brief Returns the transport endpoint.
     * @return Shared transport interface.
     */
    std::shared_ptr<rogue::protocols::rssi::Transport> transport();

    /**
     * @brief Returns the application endpoint.
     * @return Shared application interface.
     */
    std::shared_ptr<rogue::protocols::rssi::Application> application();

    /**
     * @brief Returns whether the link is open.
     * @return True when the RSSI link is open.
     */
    bool getOpen();

    /**
     * @brief Returns the down-transition counter.
     * @return Number of times the link entered a down/closed state.
     */
    uint32_t getDownCount();

    /**
     * @brief Returns the dropped-frame counter.
     * @return Number of dropped received frames.
     */
    uint32_t getDropCount();

    /**
     * @brief Returns the retransmit counter.
     * @return Number of retransmitted frames.
     */
    uint32_t getRetranCount();

    /**
     * @brief Returns the local busy state.
     * @return True when the local endpoint is currently busy.
     */
    bool getLocBusy();

    /**
     * @brief Returns the local busy event counter.
     * @return Number of local busy assertions.
     */
    uint32_t getLocBusyCnt();

    /**
     * @brief Returns the remote busy state.
     * @return True when the remote endpoint reports busy.
     */
    bool getRemBusy();

    /**
     * @brief Returns the remote busy event counter.
     * @return Number of remote busy indications.
     */
    uint32_t getRemBusyCnt();

    /** @brief Sets the local connection retry period in microseconds. */
    void setLocTryPeriod(uint32_t val);
    /** @brief Returns the local connection retry period in microseconds. */
    uint32_t getLocTryPeriod();

    /** @brief Sets the local maximum outstanding-buffer count. */
    void setLocMaxBuffers(uint8_t val);
    /** @brief Returns the local maximum outstanding-buffer count. */
    uint8_t getLocMaxBuffers();

    /** @brief Sets the local maximum segment size in bytes. */
    void setLocMaxSegment(uint16_t val);
    /** @brief Returns the local maximum segment size in bytes. */
    uint16_t getLocMaxSegment();

    /** @brief Sets the local cumulative-ACK timeout. */
    void setLocCumAckTout(uint16_t val);
    /** @brief Returns the local cumulative-ACK timeout. */
    uint16_t getLocCumAckTout();

    /** @brief Sets the local retransmit timeout. */
    void setLocRetranTout(uint16_t val);
    /** @brief Returns the local retransmit timeout. */
    uint16_t getLocRetranTout();

    /** @brief Sets the local null-segment timeout. */
    void setLocNullTout(uint16_t val);
    /** @brief Returns the local null-segment timeout. */
    uint16_t getLocNullTout();

    /** @brief Sets the local maximum retransmit count. */
    void setLocMaxRetran(uint8_t val);
    /** @brief Returns the local maximum retransmit count. */
    uint8_t getLocMaxRetran();

    /** @brief Sets the local maximum cumulative-ACK interval. */
    void setLocMaxCumAck(uint8_t val);
    /** @brief Returns the local maximum cumulative-ACK interval. */
    uint8_t getLocMaxCumAck();

    /** @brief Returns the negotiated maximum outstanding-buffer count. */
    uint8_t curMaxBuffers();
    /** @brief Returns the negotiated maximum segment size in bytes. */
    uint16_t curMaxSegment();
    /** @brief Returns the negotiated cumulative-ACK timeout. */
    uint16_t curCumAckTout();
    /** @brief Returns the negotiated retransmit timeout. */
    uint16_t curRetranTout();
    /** @brief Returns the negotiated null-segment timeout. */
    uint16_t curNullTout();
    /** @brief Returns the negotiated maximum retransmit count. */
    uint8_t curMaxRetran();
    /** @brief Returns the negotiated maximum cumulative-ACK interval. */
    uint8_t curMaxCumAck();

    /** @brief Resets runtime counters. */
    void resetCounters();

    /**
     * @brief Sets timeout in microseconds for frame transmits.
     * @param timeout Timeout in microseconds.
     */
    void setTimeout(uint32_t timeout);

    /** @brief Stops the RSSI connection. */
    void stop();

    /** @brief Starts or restarts RSSI connection establishment. */
    void start();
};

// Convienence
typedef std::shared_ptr<rogue::protocols::rssi::Server> ServerPtr;

}  // namespace rssi
}  // namespace protocols
};  // namespace rogue

#endif
