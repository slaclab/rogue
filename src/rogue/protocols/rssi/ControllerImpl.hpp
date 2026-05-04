/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * RSSI Controller — lower half: state machine, retransmit, flow control,
 * timer, and OOO queue management.  Extracted from Controller.cpp to bring
 * the primary source file below the 600-line maintainability threshold.
 * Included only by Controller.cpp; not a public header.
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

// -- accessors ---------------------------------------------------------------

uint8_t rpr::Controller::curMaxRetran() {
    return curMaxRetran_;
}

uint8_t rpr::Controller::curMaxCumAck() {
    return curMaxCumAck_;
}

void rpr::Controller::resetCounters() {
    dropCount_   = 0;
    downCount_   = 0;
    retranCount_ = 0;
    locBusyCnt_  = 0;
    remBusyCnt_  = 0;
}

// -- transport helpers -------------------------------------------------------

// Method to transit a frame with proper updates
void rpr::Controller::transportTx(rpr::HeaderPtr head, bool seqUpdate, bool txReset) {
    std::unique_lock<std::mutex> lock(txMtx_);

    head->sequence = locSequence_;

    // Update sequence numbers
    if (seqUpdate) {
        txList_[locSequence_] = head;
        txListCount_++;
        locSequence_++;
    }

    // Reset tx list
    if (txReset) {
        for (uint32_t x = 0; x < 256; x++) txList_[x].reset();
        txListCount_ = 0;
    }

    if (getLocBusy()) {
        head->acknowledge = lastAckTx_;
        head->busy        = true;
    } else {
        head->acknowledge = ackSeqRx_;
        lastAckTx_        = ackSeqRx_;
        head->busy        = false;
    }

    // Track last tx time
    gettimeofday(&txTime_, NULL);

    ris::FrameLockPtr flock = head->getFrame()->lock();
    head->update();

    log_->log(rogue::Logging::Debug,
              "TX frame: state=%" PRIu32 " server=%d size=%" PRIu32 " syn=%d ack=%d nul=%d"
              ", bsy=%d, rst=%d, ack#=%" PRIu8 ", seq=%" PRIu8 ", recount=%" PRIu32 ", ptr=%p",
              state_,
              server_,
              head->getFrame()->getPayload(),
              head->syn,
              head->ack,
              head->nul,
              head->busy,
              head->rst,
              head->acknowledge,
              head->sequence,
              retranCount_.load(),
              static_cast<void*>(head->getFrame().get()));

    flock->unlock();
    lock.unlock();

    // Send frame
    tran_->sendFrame(head->getFrame());
}

// Method to retransmit a frame
int8_t rpr::Controller::retransmit(uint8_t id) {
    std::unique_lock<std::mutex> lock(txMtx_);

    rpr::HeaderPtr head = txList_[id];
    if (head == NULL) return 0;

    // retransmit timer has not expired
    if (!timePassed(head->getTime(), retranToutD1_)) return 0;

    // max retransmission count has been reached
    if (head->count() >= curMaxRetran_) return -1;

    retranCount_++;

    if (getLocBusy()) {
        head->acknowledge = lastAckTx_;
        head->busy        = true;
    } else {
        head->acknowledge = ackSeqRx_;
        lastAckTx_        = ackSeqRx_;
        head->busy        = false;
    }

    // Track last tx time
    gettimeofday(&txTime_, NULL);

    log_->log(rogue::Logging::Warning,
              "Retran frame: state=%" PRIu32 " server=%d size=%" PRIu32 " syn=%d ack=%d"
              " nul=%d, rst=%d, ack#=%" PRIu8 ", seq=%" PRIu8 ", recount=%" PRIu32 ", ptr=%p",
              state_,
              server_,
              head->getFrame()->getPayload(),
              head->syn,
              head->ack,
              head->nul,
              head->rst,
              head->acknowledge,
              head->sequence,
              retranCount_.load(),
              static_cast<void*>(head->getFrame().get()));

    ris::FrameLockPtr flock = head->getFrame()->lock();
    head->update();
    flock->unlock();
    lock.unlock();

    // Send frame
    tran_->sendFrame(head->getFrame());
    return 1;
}

// -- time utilities ----------------------------------------------------------

//! Convert rssi time to microseconds
void rpr::Controller::convTime(struct timeval& tme, uint32_t rssiTime) {
    float units = std::pow(10, -TimeoutUnit);
    float value = units * static_cast<float>(rssiTime);

    uint32_t usec = static_cast<uint32_t>(value / 1e-6);

    div_t divResult = div(usec, 1000000);
    tme.tv_sec      = divResult.quot;
    tme.tv_usec     = divResult.rem;
}

//! Helper function to determine if time has elapsed
bool rpr::Controller::timePassed(struct timeval& lastTime, struct timeval& tme) {
    struct timeval endTime;
    struct timeval currTime;

    gettimeofday(&currTime, NULL);
    timeradd(&lastTime, &tme, &endTime);
    return (timercmp(&currTime, &endTime, >=));
}

// -- background thread -------------------------------------------------------

//! Background thread
void rpr::Controller::runThread() {
    struct timeval wait;

    log_->logThreadId();

    wait = zeroTme_;

    while (threadEn_) {
        // Lock context
        if (wait.tv_sec != 0 || wait.tv_usec != 0) {
            // Wait on condition or timeout
            std::unique_lock<std::mutex> lock(stMtx_);

            // Adjustable wait
            stCond_.wait_for(lock, std::chrono::microseconds(wait.tv_usec) + std::chrono::seconds(wait.tv_sec));
        }

        switch (state_) {
            case StClosed:
            case StWaitSyn:
                wait = stateClosedWait();
                break;

            case StSendSynAck:
                wait = stateSendSynAck();
                break;

            case StSendSeqAck:
                wait = stateSendSeqAck();
                break;

            case StOpen:
                wait = stateOpen();
                break;

            case StError:
                wait = stateError();
                break;
            default:
                break;
        }
    }

    // Send reset on exit
    stateError();
}

// -- state machine -----------------------------------------------------------

//! Closed/Waiting for Syn
struct timeval& rpr::Controller::stateClosedWait() {
    rpr::HeaderPtr head;

    // got syn or reset
    if (!stQueue_.empty()) {
        head = stQueue_.pop();

        // Reset
        if (head->rst) {
            state_ = StClosed;
            log_->warning("Closing link after reset request. Server=%d", server_);

            // Syn ack
        } else if (head->syn && (head->ack || server_)) {
            curMaxBuffers_ = head->maxOutstandingSegments;
            curMaxSegment_ = head->maxSegmentSize;
            curCumAckTout_ = head->cumulativeAckTimeout;
            curRetranTout_ = head->retransmissionTimeout;
            curNullTout_   = head->nullTimeout;
            curMaxRetran_  = head->maxRetransmissions;
            curMaxCumAck_  = head->maxCumulativeAck;
            lastAckRx_     = head->acknowledge;

            // Convert times
            convTime(retranToutD1_, curRetranTout_);
            convTime(cumAckToutD1_, curCumAckTout_);
            convTime(cumAckToutD2_, curCumAckTout_ / 2);
            convTime(nullToutD3_, curNullTout_ / 3);

            if (server_) {
                state_ = StSendSynAck;
                return (zeroTme_);
            } else {
                state_ = StSendSeqAck;
            }
            gettimeofday(&stTime_, NULL);

            // reset counters
        } else {
            curMaxBuffers_ = locMaxBuffers_;
            curMaxSegment_ = locMaxSegment_;
            curCumAckTout_ = locCumAckTout_;
            curRetranTout_ = locRetranTout_;
            curNullTout_   = locNullTout_;
            curMaxRetran_  = locMaxRetran_;
            curMaxCumAck_  = locMaxCumAck_;
        }

        // Generate syn after try period passes
    } else if ((!server_) && timePassed(stTime_, tryPeriodD1_)) {
        // Allocate frame
        head = rpr::Header::create(tran_->reqFrame(rpr::Header::SynSize, false));

        // Set frame
        head->syn                    = true;
        head->version                = Version;
        head->chk                    = true;
        head->maxOutstandingSegments = locMaxBuffers_;
        head->maxSegmentSize         = locMaxSegment_;
        head->retransmissionTimeout  = locRetranTout_;
        head->cumulativeAckTimeout   = locCumAckTout_;
        head->nullTimeout            = locNullTout_;
        head->maxRetransmissions     = locMaxRetran_;
        head->maxCumulativeAck       = locMaxCumAck_;
        head->timeoutUnit            = TimeoutUnit;
        head->connectionId           = locConnId_;

        transportTx(head, true, false);

        // Update state
        gettimeofday(&stTime_, NULL);
        state_ = StWaitSyn;
    } else if (server_) {
        state_ = StWaitSyn;
    }

    return (tryPeriodD4_);
}

//! Send Syn ack
struct timeval& rpr::Controller::stateSendSynAck() {
    // Allocate frame
    rpr::HeaderPtr head = rpr::Header::create(tran_->reqFrame(rpr::Header::SynSize, false));

    // Set frame
    head->syn                    = true;
    head->ack                    = true;
    head->version                = Version;
    head->chk                    = true;
    head->maxOutstandingSegments = curMaxBuffers_;
    head->maxSegmentSize         = curMaxSegment_;
    head->retransmissionTimeout  = curRetranTout_;
    head->cumulativeAckTimeout   = curCumAckTout_;
    head->nullTimeout            = curNullTout_;
    head->maxRetransmissions     = curMaxRetran_;
    head->maxCumulativeAck       = curMaxCumAck_;
    head->timeoutUnit            = TimeoutUnit;
    head->connectionId           = locConnId_;

    transportTx(head, true, true);

    // Update state
    log_->info("Link state is open. Server=%d", server_);
    state_ = StOpen;
    return (cumAckToutD2_);
}

//! Send sequence ack
struct timeval& rpr::Controller::stateSendSeqAck() {
    // Allocate frame
    rpr::HeaderPtr ack = rpr::Header::create(tran_->reqFrame(rpr::Header::HeaderSize, false));

    // Setup frame
    ack->ack  = true;
    ack->nul  = false;
    ackSeqRx_ = lastSeqRx_;

    transportTx(ack, false, true);

    // Update state
    state_ = StOpen;
    log_->info("Link state is open. Server=%d", server_);
    return (cumAckToutD2_);
}

//! Idle with open state
struct timeval& rpr::Controller::stateOpen() {
    rpr::HeaderPtr head;
    uint8_t idx;
    bool doNull;
    uint8_t ackPend;
    struct timeval locTime;

    // Pending frame may be reset
    while (!stQueue_.empty()) {
        head = stQueue_.pop();

        // Reset or syn without ack is an error
        if ((head->rst) || (head->syn && (!head->ack))) {
            state_ = StError;
            gettimeofday(&stTime_, NULL);
            return (zeroTme_);
        }
    }

    // Sample transmit time and compute pending ack count under lock
    {
        std::unique_lock<std::mutex> lock(txMtx_);
        locTime = txTime_;
        ackPend = ackSeqRx_ - lastAckTx_;
    }

    // NULL required
    if (timePassed(locTime, nullToutD3_))
        doNull = true;
    else
        doNull = false;

    // Outbound frame required
    if ((doNull || ((!getLocBusy()) && ackPend >= curMaxCumAck_) ||
         ((ackPend > 0 || getLocBusy()) && timePassed(locTime, cumAckToutD1_)))) {
        head      = rpr::Header::create(tran_->reqFrame(rpr::Header::HeaderSize, false));
        head->ack = true;
        head->nul = doNull;
        transportTx(head, doNull, false);
    }

    // Retransmission processing, don't process when busy
    idx = lastAckRx_;
    while ((!remBusy_) && (idx != locSequence_)) {
        if (retransmit(idx++) < 0) {
            state_ = StError;
            gettimeofday(&stTime_, NULL);
            return (zeroTme_);
        }
    }

    return (cumAckToutD2_);
}

//! Error
struct timeval& rpr::Controller::stateError() {
    rpr::HeaderPtr rst;

    log_->warning("Entering reset state. Server=%d", server_);

    rst      = rpr::Header::create(tran_->reqFrame(rpr::Header::HeaderSize, false));
    rst->rst = true;

    transportTx(rst, true, true);

    downCount_++;
    log_->warning("Entering closed state after reset. Server=%d", server_);
    state_ = StClosed;

    // Reset queues
    appQueue_.reset();
    oooQueue_.clear();
    stQueue_.reset();

    gettimeofday(&stTime_, NULL);
    return (tryPeriodD1_);
}

//! Set timeout for frame transmits in microseconds
void rpr::Controller::setTimeout(uint32_t timeout) {
    div_t divResult  = div(timeout, 1000000);
    timeout_.tv_sec  = divResult.quot;
    timeout_.tv_usec = divResult.rem;
}
