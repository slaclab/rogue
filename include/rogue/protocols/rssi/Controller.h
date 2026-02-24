/**
  * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 *      RSSI Controller Class
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
#ifndef __ROGUE_PROTOCOLS_RSSI_CONTROLLER_H__
#define __ROGUE_PROTOCOLS_RSSI_CONTROLLER_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <map>
#include <memory>

#include "rogue/EnableSharedFromThis.h"
#include "rogue/Logging.h"
#include "rogue/Queue.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"

namespace rogue {
namespace protocols {
namespace rssi {

class Application;
class Transport;
class Header;

/**
 * @brief RSSI protocol controller.
 * Implements connection state, flow control, retransmission, and parameter
 *  negotiation between RSSI application and transport endpoints.
 */
class Controller : public rogue::EnableSharedFromThis<rogue::protocols::rssi::Controller> {
    //! Hard coded values
    static const uint8_t Version     = 1;
    static const uint8_t TimeoutUnit = 3;  // rssiTime * std::pow(10,-TimeoutUnit) = 3 = ms

    //! Local parameters
    uint32_t locTryPeriod_;

    //! Configurable parameters, requested by software
    uint8_t locMaxBuffers_;
    uint16_t locMaxSegment_;
    uint16_t locCumAckTout_;
    uint16_t locRetranTout_;
    uint16_t locNullTout_;
    uint8_t locMaxRetran_;
    uint8_t locMaxCumAck_;

    //! Negotiated parameters
    uint8_t curMaxBuffers_;
    uint16_t curMaxSegment_;
    uint16_t curCumAckTout_;
    uint16_t curRetranTout_;
    uint16_t curNullTout_;
    uint8_t curMaxRetran_;
    uint8_t curMaxCumAck_;

    //! Connection states
    enum States : uint32_t { StClosed = 0, StWaitSyn = 1, StSendSynAck = 2, StSendSeqAck = 3, StOpen = 4, StError = 5 };

    // Interfaces
    std::shared_ptr<rogue::protocols::rssi::Transport> tran_;
    std::shared_ptr<rogue::protocols::rssi::Application> app_;

    std::shared_ptr<rogue::Logging> log_;

    // Is server
    bool server_;

    // Receive tracking
    uint32_t dropCount_;
    uint8_t nextSeqRx_;
    uint8_t lastAckRx_;
    bool remBusy_;
    bool locBusy_;

    // Application queue
    rogue::Queue<std::shared_ptr<rogue::protocols::rssi::Header>> appQueue_;

    // Sequence Out of Order ("OOO") queue
    std::map<uint8_t, std::shared_ptr<rogue::protocols::rssi::Header>> oooQueue_;

    // State queue
    rogue::Queue<std::shared_ptr<rogue::protocols::rssi::Header>> stQueue_;

    // Application tracking
    uint8_t lastSeqRx_;
    uint8_t ackSeqRx_;

    // State Tracking
    std::condition_variable stCond_;
    std::mutex stMtx_;
    uint32_t state_;
    struct timeval stTime_;
    uint32_t downCount_;
    uint32_t retranCount_;
    uint32_t locBusyCnt_;
    uint32_t remBusyCnt_;
    uint32_t locConnId_;
    uint32_t remConnId_;

    // Transmit tracking
    std::shared_ptr<rogue::protocols::rssi::Header> txList_[256];
    std::mutex txMtx_;
    uint8_t txListCount_;
    uint8_t lastAckTx_;
    uint8_t locSequence_;
    struct timeval txTime_;

    // Time values
    struct timeval retranToutD1_;  // retranTout_ / 1
    struct timeval tryPeriodD1_;   // TryPeriod   / 1
    struct timeval tryPeriodD4_;   // TryPeriod   / 4
    struct timeval cumAckToutD1_;  // cumAckTout_ / 1
    struct timeval cumAckToutD2_;  // cumAckTout_ / 2
    struct timeval nullToutD3_;    // nullTout_   / 3
    struct timeval zeroTme_;       // 0

    // State thread
    std::thread* thread_;
    bool threadEn_;

    // Application frame transmit timeout
    struct timeval timeout_;

  public:
    //! Class creation
    static std::shared_ptr<rogue::protocols::rssi::Controller> create(
        uint32_t segSize,
        std::shared_ptr<rogue::protocols::rssi::Transport> tran,
        std::shared_ptr<rogue::protocols::rssi::Application> app,
        bool server);

    /**
     * Construct an RSSI controller.
     * @param[in] segSize Initial local max segment size.
     *  @param[in] tran Transport endpoint used for link traffic.
     *  @param[in] app Application endpoint used for payload traffic.
     *  @param[in] server True to run the server-side handshake behavior.
     */
    Controller(uint32_t segSize,
               std::shared_ptr<rogue::protocols::rssi::Transport> tran,
               std::shared_ptr<rogue::protocols::rssi::Application> app,
               bool server);

    //! Destructor
    ~Controller();

    //! Stop Queues
    void stopQueue();

    //! Transport frame allocation request
    std::shared_ptr<rogue::interfaces::stream::Frame> reqFrame(uint32_t size);

    /**
     * Process a frame received from transport.
     * @param[in] frame Input frame from transport endpoint.
     */
    void transportRx(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    /**
     * Get next frame to transmit from the application side.
     * @return Frame ready for transmit, or null when none is available.
     */
    std::shared_ptr<rogue::interfaces::stream::Frame> applicationTx();

    /**
     * Process a frame received from the application side.
     * @param[in] frame Input frame from application endpoint.
     */
    void applicationRx(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    /**
     * Return whether the RSSI link is in open state.
     * @return True when connection state is open.
     */
    bool getOpen();

    /**
     * Return link down transition counter.
     * @return Number of times link entered down/closed state.
     */
    uint32_t getDownCount();

    /**
     * Return dropped-frame counter.
     * @return Number of dropped received frames.
     */
    uint32_t getDropCount();

    /**
     * Return retransmit counter.
     * @return Number of retransmitted frames.
     */
    uint32_t getRetranCount();

    /**
     * Return local busy state.
     * @return True when local endpoint is currently busy.
     */
    bool getLocBusy();

    /**
     * Return local busy event counter.
     * @return Number of local busy assertions.
     */
    uint32_t getLocBusyCnt();

    /**
     * Return remote busy state.
     * @return True when remote endpoint reports busy.
     */
    bool getRemBusy();

    /**
     * Return remote busy event counter.
     * @return Number of remote busy indications seen.
     */
    uint32_t getRemBusyCnt();

    /**
     * Set local connection retry period.
     * @param[in] val Retry period in microseconds.
     */
    void setLocTryPeriod(uint32_t val);
    /**
     * Get local connection retry period.
     * @return Retry period in microseconds.
     */
    uint32_t getLocTryPeriod();

    /**
     * Set local max outstanding buffers parameter.
     * @param[in] val Maximum outstanding buffers.
     */
    void setLocMaxBuffers(uint8_t val);
    /**
     * Get local max outstanding buffers parameter.
     * @return Maximum outstanding buffers.
     */
    uint8_t getLocMaxBuffers();

    /**
     * Set local max segment size.
     * @param[in] val Segment size in bytes.
     */
    void setLocMaxSegment(uint16_t val);
    /**
     * Get local max segment size.
     * @return Segment size in bytes.
     */
    uint16_t getLocMaxSegment();

    /**
     * Set local cumulative ACK timeout.
     * @param[in] val Timeout in protocol time units.
     */
    void setLocCumAckTout(uint16_t val);
    /**
     * Get local cumulative ACK timeout.
     * @return Timeout in protocol time units.
     */
    uint16_t getLocCumAckTout();

    /**
     * Set local retransmit timeout.
     * @param[in] val Timeout in protocol time units.
     */
    void setLocRetranTout(uint16_t val);
    /**
     * Get local retransmit timeout.
     * @return Timeout in protocol time units.
     */
    uint16_t getLocRetranTout();

    /**
     * Set local null-segment timeout.
     * @param[in] val Timeout in protocol time units.
     */
    void setLocNullTout(uint16_t val);
    /**
     * Get local null-segment timeout.
     * @return Timeout in protocol time units.
     */
    uint16_t getLocNullTout();

    /**
     * Set local max retransmit count.
     * @param[in] val Maximum retransmit attempts.
     */
    void setLocMaxRetran(uint8_t val);
    /**
     * Get local max retransmit count.
     * @return Maximum retransmit attempts.
     */
    uint8_t getLocMaxRetran();

    /**
     * Set local max cumulative ACK interval.
     * @param[in] val Maximum number of packets before cumulative ACK.
     */
    void setLocMaxCumAck(uint8_t val);
    /**
     * Get local max cumulative ACK interval.
     * @return Maximum number of packets before cumulative ACK.
     */
    uint8_t getLocMaxCumAck();

    /**
     * Get negotiated max outstanding buffers.
     * @return Negotiated max outstanding buffers.
     */
    uint8_t curMaxBuffers();
    /**
     * Get negotiated max segment size.
     * @return Negotiated segment size in bytes.
     */
    uint16_t curMaxSegment();
    /**
     * Get negotiated cumulative ACK timeout.
     * @return Negotiated timeout in protocol time units.
     */
    uint16_t curCumAckTout();
    /**
     * Get negotiated retransmit timeout.
     * @return Negotiated timeout in protocol time units.
     */
    uint16_t curRetranTout();
    /**
     * Get negotiated null-segment timeout.
     * @return Negotiated timeout in protocol time units.
     */
    uint16_t curNullTout();
    /**
     * Get negotiated max retransmit count.
     * @return Negotiated max retransmit attempts.
     */
    uint8_t curMaxRetran();
    /**
     * Get negotiated max cumulative ACK interval.
     * @return Negotiated packets between cumulative ACKs.
     */
    uint8_t curMaxCumAck();

    /** Reset runtime counters. */
    void resetCounters();

    /** Set timeout in microseconds for frame transmits */
    void setTimeout(uint32_t timeout);

    /** Stop the RSSI connection and worker thread. */
    void stop();

    /** Start or restart RSSI connection establishment. */
    void start();

  private:
    // Method to transit a frame with proper updates
    void transportTx(std::shared_ptr<rogue::protocols::rssi::Header> head, bool seqUpdate, bool txReset);

    // Method to retransmit a frame
    int8_t retransmit(uint8_t id);

    /** Convert rssi time to time structure */
    static void convTime(struct timeval& tme, uint32_t rssiTime);

    /** Helper function to determine if time has elapsed in current state */
    static bool timePassed(struct timeval& lastTime, struct timeval& tme);

    /** Thread background */
    void runThread();

    /** Closed/Waiting for Syn */
    struct timeval& stateClosedWait();

    /** Send syn ack */
    struct timeval& stateSendSynAck();

    /** Send sequence ack */
    struct timeval& stateSendSeqAck();

    /** Open state */
    struct timeval& stateOpen();

    /** Error state */
    struct timeval& stateError();
};

// Convenience
typedef std::shared_ptr<rogue::protocols::rssi::Controller> ControllerPtr;

}  // namespace rssi
}  // namespace protocols
};  // namespace rogue

#endif
