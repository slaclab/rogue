/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 *   RoCEv2 Server
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
#include "rogue/Directives.h"

#include "rogue/protocols/rocev2/Server.h"

#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <infiniband/verbs.h>
#include <inttypes.h>
#include <stdint.h>
#include <string.h>
#include <sys/select.h>
#include <unistd.h>

#include <chrono>
#include <cstdlib>
#include <iomanip>
#include <memory>
#include <random>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

#include "rogue/GeneralError.h"
#include "rogue/GilRelease.h"
#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Buffer.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/FrameLock.h"
#include "rogue/protocols/rocev2/Core.h"

namespace rpr = rogue::protocols::rocev2;
namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
    #include <boost/python.hpp>
namespace bp = boost::python;
#endif

// SSI Start-of-Frame bit set on every received frame
static const uint8_t SsiSof = 0x02;

// ---------------------------------------------------------------------------
// Factory
// ---------------------------------------------------------------------------
rpr::ServerPtr rpr::Server::create(const std::string& deviceName,
                                   uint8_t            ibPort,
                                   uint8_t            gidIndex,
                                   uint32_t           maxPayload,
                                   uint32_t           rxQueueDepth) {
    return std::make_shared<rpr::Server>(
        deviceName, ibPort, gidIndex, maxPayload, rxQueueDepth);
}

// ---------------------------------------------------------------------------
// Constructor
// ibverbs setup through QP INIT.  Receive thread starts in
// completeConnection() once the FPGA QPN is known.
// ---------------------------------------------------------------------------
rpr::Server::Server(const std::string& deviceName,
                    uint8_t            ibPort,
                    uint8_t            gidIndex,
                    uint32_t           maxPayload,
                    uint32_t           rxQueueDepth)
    : rpr::Core(deviceName, ibPort, gidIndex, maxPayload),
      ris::Master(),
      ris::Slave(),
      cq_(nullptr), qp_(nullptr), mr_(nullptr), comp_channel_(nullptr),
      slab_(nullptr),
      slabSize_(0),
      numBufs_(rxQueueDepth),
      bufSize_(0),
      hostQpn_(0),
      hostRqPsn_(0),
      hostSqPsn_(0),
      mrAddr_(0),
      mrRkey_(0),
      thread_(nullptr),
      threadEn_(false),
      frameCount_(0),
      byteCount_(0) {

    log_ = rogue::Logging::create("rocev2.Server");
    memset(hostGid_, 0, 16);
    memset(fpgaGid_, 0, 16);
    wakeFd_[0] = wakeFd_[1] = -1;

    // The destructor does NOT run on a partially-constructed object, so any
    // throw between here and the end of the body would leak slab_ / mr_ /
    // cq_ / qp_.  Wrap the body in try/catch and call cleanupResources() on
    // the way out before rethrowing — same effect as a stack of unique_ptr
    // wrappers but with a single cleanup path.
    try {
        // -------------------------------------------------------------------
        // 1. Allocate slab
        //    RC QPs do not prepend a GRH so each slot is exactly maxPayload_.
        //    posix_memalign accepts any size (aligned_alloc requires the size
        //    to be a multiple of the alignment per C11; with the default
        //    9000 * 256 slab that constraint does not hold).
        // -------------------------------------------------------------------
        bufSize_  = maxPayload_;

        uint64_t slabSize64 = static_cast<uint64_t>(numBufs_) * bufSize_;
        if (slabSize64 > UINT32_MAX)
            throw(rogue::GeneralError::create("rocev2::Server::Server",
                                              "RX slab too large: %u * %u = %" PRIu64 " exceeds 4 GiB",
                                              numBufs_, bufSize_, slabSize64));
        slabSize_ = static_cast<uint32_t>(slabSize64);

        void* slabPtr = nullptr;
        if (posix_memalign(&slabPtr, 4096, slabSize_) != 0 || !slabPtr)
            throw(rogue::GeneralError::create("rocev2::Server::Server",
                                              "Failed to allocate RX slab (%u bytes)",
                                              slabSize_));
        slab_ = static_cast<uint8_t*>(slabPtr);
        memset(slab_, 0, slabSize_);

        // -------------------------------------------------------------------
        // 2. Register slab as a single MR
        // -------------------------------------------------------------------
        mr_ = ibv_reg_mr(pd_, slab_, slabSize_,
                         IBV_ACCESS_LOCAL_WRITE | IBV_ACCESS_REMOTE_WRITE);
        if (!mr_)
            throw(rogue::GeneralError::create("rocev2::Server::Server",
                                              "ibv_reg_mr failed"));

        mrAddr_ = reinterpret_cast<uint64_t>(slab_);
        mrRkey_ = mr_->rkey;

        log_->info("MR: addr=0x%016" PRIx64 " rkey=0x%08x size=%u",
                   mrAddr_, mrRkey_, slabSize_);

        // -------------------------------------------------------------------
        // 3a. Completion channel + self-pipe (event-driven CQ, no busy-poll)
        //     The CQ below is bound to comp_channel_ so each completion makes
        //     the channel fd readable; runThread() blocks in select() on that
        //     fd plus wakeFd_ (a self-pipe stop() writes to) for prompt,
        //     sleepless shutdown. Both fds are non-blocking so the drain loops
        //     terminate cleanly (ibv_get_cq_event returns EAGAIN when empty).
        // -------------------------------------------------------------------
        comp_channel_ = ibv_create_comp_channel(ctx_);
        if (!comp_channel_)
            throw(rogue::GeneralError::create("rocev2::Server::Server",
                                              "ibv_create_comp_channel failed"));
        {
            int flags = fcntl(comp_channel_->fd, F_GETFL);
            if (flags < 0 ||
                fcntl(comp_channel_->fd, F_SETFL, flags | O_NONBLOCK) < 0)
                throw(rogue::GeneralError::create("rocev2::Server::Server",
                                                  "failed to set comp channel fd non-blocking"));
        }

        if (pipe(wakeFd_) != 0)
            throw(rogue::GeneralError::create("rocev2::Server::Server",
                                              "wake self-pipe creation failed"));
        for (int i = 0; i < 2; ++i) {
            int flags = fcntl(wakeFd_[i], F_GETFL);
            if (flags >= 0) fcntl(wakeFd_[i], F_SETFL, flags | O_NONBLOCK);
        }

        // -------------------------------------------------------------------
        // 3. Create Completion Queue (bound to comp_channel_ for event-driven
        //    notification; cq_context = this)
        // -------------------------------------------------------------------
        cq_ = ibv_create_cq(ctx_,
                             static_cast<int>(numBufs_),
                             this, comp_channel_, 0);
        if (!cq_)
            throw(rogue::GeneralError::create("rocev2::Server::Server",
                                              "ibv_create_cq failed"));

        // -------------------------------------------------------------------
        // 4. Create RC Queue Pair
        // -------------------------------------------------------------------
        struct ibv_qp_init_attr qpAttr;
        memset(&qpAttr, 0, sizeof(qpAttr));
        qpAttr.qp_type          = IBV_QPT_RC;
        qpAttr.sq_sig_all       = 0;
        qpAttr.send_cq          = cq_;
        qpAttr.recv_cq          = cq_;
        qpAttr.cap.max_recv_wr  = numBufs_;
        qpAttr.cap.max_send_wr  = 1;
        qpAttr.cap.max_recv_sge = 1;
        qpAttr.cap.max_send_sge = 1;

        qp_ = ibv_create_qp(pd_, &qpAttr);
        if (!qp_)
            throw(rogue::GeneralError::create("rocev2::Server::Server",
                                              "ibv_create_qp (RC) failed"));

        hostQpn_ = qp_->qp_num;

        // -------------------------------------------------------------------
        // 5. QP: RESET → INIT
        // -------------------------------------------------------------------
        {
            struct ibv_qp_attr attr;
            memset(&attr, 0, sizeof(attr));
            attr.qp_state        = IBV_QPS_INIT;
            attr.pkey_index      = 0;
            attr.port_num        = ibPort_;
            attr.qp_access_flags = IBV_ACCESS_REMOTE_WRITE |
                                   IBV_ACCESS_REMOTE_READ  |
                                   IBV_ACCESS_LOCAL_WRITE;

            if (ibv_modify_qp(qp_, &attr,
                              IBV_QP_STATE      |
                              IBV_QP_PKEY_INDEX |
                              IBV_QP_PORT       |
                              IBV_QP_ACCESS_FLAGS))
                throw(rogue::GeneralError::create("rocev2::Server::Server",
                                                  "QP RESET→INIT failed"));
        }

        // -------------------------------------------------------------------
        // 6. Read host GID
        //
        //    The rdma_rxe (Soft-RoCE) kernel driver does NOT validate
        //    gidIndex against the populated range of its GID table —
        //    ibv_query_gid returns rc=0 for any in-range index per the
        //    reported gid_tbl_len (1024 on RXE) and silently writes an
        //    all-zero GID for unpopulated slots.  A zero GID passes the
        //    rc==0 check here but cripples the later QP→RTR transition
        //    (dest GID cannot resolve to a peer), producing a cryptic
        //    downstream failure whose trail back to the bad gidIndex is
        //    obscured.  Validate the returned GID is non-zero so users
        //    get a clear, actionable error pinned to the gidIndex they
        //    actually passed — valid RoCE GIDs are never all-zero
        //    (IPv4-mapped carries the 0xFFFF marker, IB-native uses an
        //    fe80::/10 or assigned subnet prefix).
        // -------------------------------------------------------------------
        union ibv_gid gid;
        if (ibv_query_gid(ctx_, ibPort_, gidIndex_, &gid))
            throw(rogue::GeneralError::create("rocev2::Server::Server",
                                              "ibv_query_gid failed"));
        bool zeroGid = true;
        for (int i = 0; i < 16; ++i) {
            if (gid.raw[i] != 0) {
                zeroGid = false;
                break;
            }
        }
        if (zeroGid)
            throw(rogue::GeneralError::create("rocev2::Server::Server",
                                              "GID query returned all-zero for "
                                              "gidIndex=%u on device '%s' "
                                              "(likely out-of-range; rdma_rxe "
                                              "does not validate gidIndex and "
                                              "returns an empty GID for unused "
                                              "slots)",
                                              gidIndex_,
                                              deviceName_.c_str()));
        memcpy(hostGid_, gid.raw, 16);

        // -------------------------------------------------------------------
        // 7. Random starting PSNs (seeded per construction to avoid
        //    deterministic sequences across process restarts; RC QP PSN is
        //    expected to be randomized to reduce stale/replay confusion).
        // -------------------------------------------------------------------
        std::mt19937 psnRng(std::random_device {}());
        hostRqPsn_ = psnRng() & 0xFFFFFF;
        hostSqPsn_ = psnRng() & 0xFFFFFF;

        log_->info("RC QP ready: qpn=0x%06x rqPsn=0x%06x sqPsn=0x%06x",
                   hostQpn_, hostRqPsn_, hostSqPsn_);
    } catch (...) {
        cleanupResources();
        throw;
    }
}

// ---------------------------------------------------------------------------
// cleanupResources — release every ibverbs / heap resource owned by Server,
// in reverse order of allocation.  Idempotent (safe to call from both the
// failed-construction path and stop()).
// ---------------------------------------------------------------------------
void rpr::Server::cleanupResources() {
    if (qp_) {
        ibv_destroy_qp(qp_);
        qp_ = nullptr;
    }
    if (cq_) {
        ibv_destroy_cq(cq_);
        cq_ = nullptr;
    }
    if (comp_channel_) {
        ibv_destroy_comp_channel(comp_channel_);
        comp_channel_ = nullptr;
    }
    if (mr_) {
        ibv_dereg_mr(mr_);
        mr_ = nullptr;
    }
    if (slab_) {
        free(slab_);
        slab_ = nullptr;
    }
    for (int i = 0; i < 2; ++i) {
        if (wakeFd_[i] >= 0) {
            close(wakeFd_[i]);
            wakeFd_[i] = -1;
        }
    }
}

// ---------------------------------------------------------------------------
// setFpgaGid
// ---------------------------------------------------------------------------
void rpr::Server::setFpgaGid(const std::string& gidBytes) {
    if (gidBytes.size() != 16)
        throw(rogue::GeneralError::create("rocev2::Server::setFpgaGid",
                                          "GID must be 16 bytes, got %zu",
                                          gidBytes.size()));
    memcpy(fpgaGid_, gidBytes.c_str(), 16);
    log_->info("FPGA GID stored");
}

// ---------------------------------------------------------------------------
// completeConnection — finish handshake and start receive thread
// ---------------------------------------------------------------------------
void rpr::Server::completeConnection(uint32_t fpgaQpn, uint32_t fpgaRqPsn,
                                     uint32_t pmtu, uint32_t minRnrTimer) {
    // Single-use: a second call would reassign thread_ and orphan the
    // original std::thread.  Real misuse would also be caught by
    // ibv_modify_qp rejecting INIT→RTR when the QP is already in RTS,
    // but guarding here gives a clearer error and prevents the raw
    // pointer reassignment pattern entirely.
    if (thread_ != nullptr)
        throw(rogue::GeneralError::create(
            "rocev2::Server::completeConnection",
            "completeConnection already invoked; destroy and recreate "
            "Server to re-establish the RC connection"));

    // pmtu is blindly static_cast<ibv_mtu>() below; validate the range up
    // front so a direct C++ caller (bypassing the Python wrapper which
    // already validates) can't smuggle an undefined enum value into
    // ibv_modify_qp.  Mirrors RoCEv2Server.__init__'s 1..5 check.
    if (pmtu < 1 || pmtu > 5)
        throw(rogue::GeneralError::create(
            "rocev2::Server::completeConnection",
            "pmtu must be in the range 1..5 "
            "(1=256 2=512 3=1024 4=2048 5=4096); got %u", pmtu));

    log_->info("completeConnection: fpgaQpn=0x%06x fpgaRqPsn=0x%06x minRnrTimer=%u",
               fpgaQpn, fpgaRqPsn, minRnrTimer);

    // Pre-post all receive WRs BEFORE moving to RTR so no incoming
    // RDMA WRITE-with-Immediate finds an empty RQ (which would cause RNR).
    for (uint32_t i = 0; i < numBufs_; ++i) postRecvWr(i);
    log_->info("Pre-posted %u recv WRs", numBufs_);

    // QP: INIT → RTR
    {
        union ibv_gid dgid;
        memcpy(dgid.raw, fpgaGid_, 16);

        struct ibv_qp_attr attr;
        memset(&attr, 0, sizeof(attr));
        attr.qp_state              = IBV_QPS_RTR;
        attr.path_mtu              = static_cast<ibv_mtu>(pmtu);
        attr.dest_qp_num           = fpgaQpn;
        attr.rq_psn                = fpgaRqPsn;
        attr.max_dest_rd_atomic    = 16;
        attr.min_rnr_timer         = minRnrTimer;
        attr.ah_attr.is_global     = 1;
        attr.ah_attr.grh.dgid      = dgid;
        attr.ah_attr.grh.sgid_index = gidIndex_;
        attr.ah_attr.grh.hop_limit = 64;
        attr.ah_attr.port_num      = ibPort_;
        attr.ah_attr.sl            = 0;

        if (ibv_modify_qp(qp_, &attr,
                          IBV_QP_STATE              |
                          IBV_QP_AV                 |
                          IBV_QP_PATH_MTU           |
                          IBV_QP_DEST_QPN           |
                          IBV_QP_RQ_PSN             |
                          IBV_QP_MAX_DEST_RD_ATOMIC |
                          IBV_QP_MIN_RNR_TIMER))
            throw(rogue::GeneralError::create("rocev2::Server::completeConnection",
                                              "QP INIT→RTR failed"));
    }

    log_->info("QP → RTR (minRnrTimer=%u)", minRnrTimer);

    // QP: RTR → RTS
    {
        struct ibv_qp_attr attr;
        memset(&attr, 0, sizeof(attr));
        attr.qp_state      = IBV_QPS_RTS;
        attr.sq_psn        = hostSqPsn_;
        attr.timeout       = 14;
        attr.retry_cnt     = 3;
        attr.rnr_retry     = 7;  // infinite (host SQ never transmits; cosmetic consistency)
        attr.max_rd_atomic = 16;

        if (ibv_modify_qp(qp_, &attr,
                          IBV_QP_STATE            |
                          IBV_QP_SQ_PSN           |
                          IBV_QP_TIMEOUT          |
                          IBV_QP_RETRY_CNT        |
                          IBV_QP_RNR_RETRY        |
                          IBV_QP_MAX_QP_RD_ATOMIC))
            throw(rogue::GeneralError::create("rocev2::Server::completeConnection",
                                              "QP RTR→RTS failed"));
    }

    log_->info("QP → RTS — ready to receive RDMA SENDs");

    // Start receive thread
    std::shared_ptr<int> scopePtr = std::make_shared<int>(0);
    threadEn_.store(true);
    thread_ = new std::thread(&rpr::Server::runThread, this,
                              std::weak_ptr<int>(scopePtr));

#ifndef __MACH__
    pthread_setname_np(thread_->native_handle(), "RoCEv2Server");
#endif
}

// ---------------------------------------------------------------------------
// getGid
// ---------------------------------------------------------------------------
std::string rpr::Server::getGid() const {
    std::ostringstream oss;
    for (int i = 0; i < 16; i += 2) {
        if (i) oss << ':';
        oss << std::hex << std::setfill('0')
            << std::setw(2) << static_cast<int>(hostGid_[i])
            << std::setw(2) << static_cast<int>(hostGid_[i+1]);
    }
    return oss.str();
}

// ---------------------------------------------------------------------------
// postRecvWr — post a receive WR for slot `slot`
// wr_id == slot index so no lookup is needed on completion
// ---------------------------------------------------------------------------
void rpr::Server::postRecvWr(uint32_t slot) {
    // Defensive: slot indexes into slab_; a corrupted wr_id (from the CQ)
    // or meta (from retBuffer) must not produce an out-of-bounds slab
    // pointer.  Normal control flow keeps slot < numBufs_ because we set
    // wr_id = slot at post time and encode slot in meta at createBuffer
    // time, but the check is cheap and catches any future regression.
    if (slot >= numBufs_)
        throw(rogue::GeneralError::create("rocev2::Server::postRecvWr",
                                          "slot=%u out of range (numBufs=%u)",
                                          slot, numBufs_));

    uint8_t* bufStart = slab_ + (static_cast<uint64_t>(slot) * bufSize_);

    struct ibv_sge sge;
    memset(&sge, 0, sizeof(sge));
    sge.addr   = reinterpret_cast<uint64_t>(bufStart);
    sge.length = bufSize_;
    sge.lkey   = mr_->lkey;

    struct ibv_recv_wr wr;
    memset(&wr, 0, sizeof(wr));
    wr.wr_id   = static_cast<uint64_t>(slot);
    wr.sg_list = &sge;
    wr.num_sge = 1;
    wr.next    = nullptr;

    struct ibv_recv_wr* bad = nullptr;
    if (ibv_post_recv(qp_, &wr, &bad))
        throw(rogue::GeneralError::create("rocev2::Server::postRecvWr",
                                          "ibv_post_recv failed (slot=%u)", slot));
}

// ---------------------------------------------------------------------------
// retBuffer — zero-copy hook
//
// Called by Buffer::~Buffer() when the last FramePtr holding this slot is
// released by downstream.  We re-post the slot to the QP so the FPGA can
// write into it again.
//
// meta lower 24 bits = slot index (set in createBuffer() call in runThread)
// ---------------------------------------------------------------------------
void rpr::Server::retBuffer(uint8_t* data, uint32_t meta, uint32_t rawSize) {
    uint32_t slot = meta & 0x00FFFFFF;

    log_->debug("retBuffer: re-posting slot=%u", slot);

    if (threadEn_.load() && qp_) {
        try {
            postRecvWr(slot);
        } catch (...) {
            // Swallow errors during shutdown
        }
    }

    decCounter(rawSize);
}

// ---------------------------------------------------------------------------
// processCompletion — handle one receive completion (zero-copy).
// Decodes the immediate, wraps the slab slot as a rogue Buffer, and forwards it
// downstream; retBuffer() re-posts the slot's credit when downstream releases
// the buffer. On IBV_WC_WR_FLUSH_ERR (QP in ERROR) it clears threadEn_ so the
// caller's drain/poll loop exits.
// ---------------------------------------------------------------------------
void rpr::Server::processCompletion(struct ibv_wc& wc) {
    uint32_t slot = static_cast<uint32_t>(wc.wr_id);

    // Defensive: every posted WR sets wr_id = slot with slot < numBufs_; a
    // corrupted wr_id must not be dereferenced as a slab offset below.
    if (slot >= numBufs_) {
        log_->warning("CQ returned out-of-range wr_id=%" PRIu64
                      " (numBufs=%u); discarding",
                      static_cast<uint64_t>(wc.wr_id), numBufs_);
        return;
    }

    if (wc.status != IBV_WC_SUCCESS) {
        log_->warning("CQ error: %s (slot=%u)", ibv_wc_status_str(wc.status), slot);

        if (wc.status == IBV_WC_WR_FLUSH_ERR) {
            // QP transitioned to ERROR; remaining posted WRs flush with this
            // status.  Do NOT re-post — signal the poll loop to stop.
            log_->error("QP in ERROR state (WR_FLUSH_ERR); exiting CQ poll thread");
            threadEn_.store(false);
            return;
        }

        postRecvWr(slot);
        return;
    }

    // RDMA-SEND-with-immediate completes as IBV_WC_RECV with the IBV_WC_WITH_IMM
    // flag set (RDMA-WRITE-with-immediate would have been IBV_WC_RECV_RDMA_WITH_IMM).
    if (wc.opcode != IBV_WC_RECV || !(wc.wc_flags & IBV_WC_WITH_IMM)) {
        log_->warning("Unexpected opcode %d / wc_flags 0x%x (slot=%u), re-posting",
                      wc.opcode, wc.wc_flags, slot);
        postRecvWr(slot);
        return;
    }

    // Decode immediate value: bits [7:0] = channel id; bits [31:8] = the
    // free-running ring position the FPGA stamped (addrCount, informational).
    // With RDMA-SEND (two-sided) the payload landed in the CONSUMED recv-WR's
    // SGE buffer (= slot). RoCE carries imm_data in network byte order.
    uint32_t imm        = ntohl(wc.imm_data);
    uint8_t  channel    = static_cast<uint8_t>(imm & 0xFF);
    uint32_t dataSlot   = (imm >> 8) & 0x00FFFFFF;
    uint32_t payloadLen = wc.byte_len;

    if (payloadLen == 0 || payloadLen > bufSize_) {
        log_->warning("Bad payload len=%u (slot=%u), re-posting", payloadLen, slot);
        postRecvWr(slot);
        return;
    }

    // Zero-copy: the SEND landed the payload at slab_ + slot*bufSize_; wrap it
    // as a rogue Buffer. The meta is the same slot so retBuffer() re-posts THAT
    // credit when downstream releases the buffer.
    uint8_t* slotPtr = slab_ + (static_cast<uint64_t>(slot) * bufSize_);

    ris::BufferPtr buff = createBuffer(slotPtr,
                                       slot & 0x00FFFFFF,
                                       payloadLen,
                                       bufSize_);
    buff->setPayload(payloadLen);

    ris::FramePtr frame = ris::Frame::create();
    frame->appendBuffer(buff);
    frame->setChannel(channel);
    frame->setFirstUser(SsiSof);
    frame->setLastUser(0);

    log_->debug("RX wrId=%u dataSlot=%u channel=%u len=%u",
                slot, dataSlot, channel, payloadLen);

    sendFrame(frame);

    frameCount_.fetch_add(1, std::memory_order_relaxed);
    byteCount_.fetch_add(payloadLen, std::memory_order_relaxed);
}

// ---------------------------------------------------------------------------
// runThread — event-driven CQ completion loop (zero-copy, no busy-poll)
//
// Blocks in select() on the completion-channel fd (raised when the CQ delivers
// an event) and the self-pipe wakeFd_ (raised by stop()).  On a CQ event it
// drains the channel, RE-ARMS before draining the CQ — so a completion that
// lands during the drain still raises a fresh event rather than being missed —
// then processes every ready completion.  There is NO sleep(): the kernel
// parks the thread until a completion or shutdown actually occurs, so the
// receive rate is not capped by a fixed poll-then-sleep cadence.
// ---------------------------------------------------------------------------
void rpr::Server::runThread(std::weak_ptr<int> lockPtr) {
    while (!lockPtr.expired()) continue;

    log_->logThreadId();
    log_->info("RoCEv2 receive thread started (event-driven)");

    rogue::GilRelease noGil;   // Release GIL for the entire thread;
                               //  sendFrame() re-acquires via ScopedGil when
                               //  calling Python slaves.

    constexpr int kPollBatch = 16;
    struct ibv_wc wcArr[kPollBatch];

    const int cqFd   = comp_channel_->fd;
    const int wakeFd = wakeFd_[0];
    const int maxFd  = (cqFd > wakeFd ? cqFd : wakeFd) + 1;

    // The loop body is wrapped in try/catch so that an ibverbs failure
    // (postRecvWr throws rogue::GeneralError on ibv_post_recv failure) shuts the
    // thread down cleanly instead of escaping the thread entry point and
    // triggering std::terminate.
    try {
        // Active-poll while completions are flowing — no sleep and no per-batch
        // interrupt/event latency (ibv_poll_cq reads the CQ from memory). The
        // RDMA-SEND flow control is closed-loop: the FPGA self-throttles to our
        // recv-WR re-post rate, so any per-batch wait (a sleep OR a completion-
        // event/interrupt that is subject to NIC coalescing) lengthens the
        // credit-return latency, the FPGA delivers in bursts, the CQ empties
        // between batches, and throughput collapses to a bursty half-rate
        // equilibrium. Polling keeps the re-post latency low so the loop stays
        // in the full-rate regime.
        //
        // Only when the CQ has stayed empty for a bounded spin budget (the
        // source is genuinely idle, not a brief inter-batch gap) do we ARM the
        // completion channel and block in select() — parking the thread with no
        // CPU spin and no sleep until the next completion or a shutdown wake.
        constexpr uint32_t kSpinBudget = 100000;  // empty polls (~sub-us each) before parking
        uint32_t           idleSpins   = 0;

        while (threadEn_.load()) {
            int n = ibv_poll_cq(cq_, kPollBatch, wcArr);
            if (n < 0) {
                log_->error("ibv_poll_cq error (%d); exiting CQ poll thread", n);
                break;
            }
            if (n > 0) {
                for (int k = 0; k < n; ++k) processCompletion(wcArr[k]);
                idleSpins = 0;
                continue;
            }

            // CQ empty: spin a bounded number of polls so a brief inter-batch
            // gap does not pay the event-wake latency.
            if (++idleSpins < kSpinBudget) continue;
            idleSpins = 0;

            // Sustained idle: arm the channel, then re-check once (a completion
            // may have landed between the last poll and the arm) before parking.
            if (ibv_req_notify_cq(cq_, 0)) {
                log_->error("ibv_req_notify_cq failed; exiting CQ poll thread");
                break;
            }
            n = ibv_poll_cq(cq_, kPollBatch, wcArr);
            if (n < 0) {
                log_->error("ibv_poll_cq error (%d); exiting CQ poll thread", n);
                break;
            }
            if (n > 0) {
                for (int k = 0; k < n; ++k) processCompletion(wcArr[k]);
                continue;  // armed; the pending event is consumed at the next park
            }

            // Truly idle and armed: park until a completion event or a shutdown
            // wake. No timeout — the self-pipe guarantees prompt, sleepless exit.
            fd_set rfds;
            FD_ZERO(&rfds);
            FD_SET(cqFd, &rfds);
            FD_SET(wakeFd, &rfds);
            int s = select(maxFd, &rfds, nullptr, nullptr, nullptr);
            if (s < 0) {
                if (errno == EINTR) continue;
                log_->error("select() failed (errno=%d); exiting CQ poll thread", errno);
                break;
            }
            if (FD_ISSET(wakeFd, &rfds)) {
                uint8_t drainBuf[64];
                while (read(wakeFd, drainBuf, sizeof(drainBuf)) > 0) {}
                break;
            }
            if (FD_ISSET(cqFd, &rfds)) {
                // Consume every queued CQ event (fd is non-blocking) and ack
                // them as a batch so the channel fd clears, then resume polling.
                struct ibv_cq* evCq;
                void*          evCtx;
                int            events = 0;
                while (ibv_get_cq_event(comp_channel_, &evCq, &evCtx) == 0) ++events;
                if (events) ibv_ack_cq_events(cq_, events);
            }
        }
    } catch (const rogue::GeneralError& e) {
        log_->error("RoCEv2 receive thread exiting on ibverbs error: %s", e.what());
    } catch (const std::exception& e) {
        log_->error("RoCEv2 receive thread exiting on exception: %s", e.what());
    } catch (...) {
        log_->error("RoCEv2 receive thread exiting on unknown exception");
    }

    threadEn_.store(false);
    log_->info("RoCEv2 receive thread stopped");
}

// ---------------------------------------------------------------------------
// acceptFrame — TX not supported.  The parameter is required by the
// stream::Slave contract but intentionally unused; name omitted to silence
// -Wunused-parameter without a `(void)frame;` cast in the body.
// ---------------------------------------------------------------------------
void rpr::Server::acceptFrame(ris::FramePtr /*frame*/) {
    log_->warning("RoCEv2 Server::acceptFrame: TX not supported, dropping");
}

// ---------------------------------------------------------------------------
// stop / destructor
// ---------------------------------------------------------------------------
void rpr::Server::stop() {
    // Signal the thread to exit if it is still running.  Always join /
    // delete thread_ when it is non-null: runThread() may have already
    // cleared threadEn_ itself (e.g. on IBV_WC_WR_FLUSH_ERR or a caught
    // exception), which would otherwise leave thread_ joinable and cause
    // ~std::thread to terminate the process.
    threadEn_.store(false);

    // Break the receive thread out of its blocking select() immediately by
    // making wakeFd_[0] readable — no timeout/poll wait needed for shutdown.
    if (wakeFd_[1] >= 0) {
        const uint8_t one = 1;
        ssize_t wr = write(wakeFd_[1], &one, 1);
        (void)wr;  // best-effort; the thread also re-checks threadEn_
    }

    if (thread_) {
        if (thread_->joinable()) thread_->join();
        delete thread_;
        thread_ = nullptr;
    }
    cleanupResources();
}

rpr::Server::~Server() { this->stop(); }

// ---------------------------------------------------------------------------
// Python bindings
// ---------------------------------------------------------------------------
void rpr::Server::setup_python() {
#ifndef NO_PYTHON
    bp::class_<rpr::Server,
               rpr::ServerPtr,
               bp::bases<rpr::Core, ris::Master, ris::Slave>,
               boost::noncopyable>(
        "Server",
        bp::init<std::string, uint8_t, uint8_t, uint32_t, uint32_t>(
            (bp::arg("deviceName"),
             bp::arg("ibPort")        = 1,
             bp::arg("gidIndex")      = 0,
             bp::arg("maxPayload")    = rpr::DefaultMaxPayload,
             bp::arg("rxQueueDepth")  = rpr::DefaultRxQueueDepth)))
        .def("create",             &rpr::Server::create)
        .staticmethod("create")
        .def("setFpgaGid",         &rpr::Server::setFpgaGid)
        .def("completeConnection", &rpr::Server::completeConnection,
             (bp::arg("fpgaQpn"),
              bp::arg("fpgaRqPsn"),
              bp::arg("pmtu")        = 5,
              bp::arg("minRnrTimer") = 1))
        .def("getQpn",             &rpr::Server::getQpn)
        .def("getGid",             &rpr::Server::getGid)
        .def("getRqPsn",           &rpr::Server::getRqPsn)
        .def("getSqPsn",           &rpr::Server::getSqPsn)
        .def("getMrAddr",          &rpr::Server::getMrAddr)
        .def("getMrRkey",          &rpr::Server::getMrRkey)
        .def("getFrameCount",      &rpr::Server::getFrameCount)
        .def("getByteCount",       &rpr::Server::getByteCount)
        .def("stop",               &rpr::Server::stop);

    bp::implicitly_convertible<rpr::ServerPtr, rpr::CorePtr>();
    bp::implicitly_convertible<rpr::ServerPtr, ris::MasterPtr>();
    bp::implicitly_convertible<rpr::ServerPtr, ris::SlavePtr>();
#endif
}
