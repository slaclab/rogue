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

#include <infiniband/verbs.h>
#include <inttypes.h>
#include <stdint.h>
#include <string.h>

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
      cq_(nullptr), qp_(nullptr), mr_(nullptr),
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
        // 3. Create Completion Queue
        // -------------------------------------------------------------------
        cq_ = ibv_create_cq(ctx_,
                             static_cast<int>(numBufs_),
                             nullptr, nullptr, 0);
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
    if (mr_) {
        ibv_dereg_mr(mr_);
        mr_ = nullptr;
    }
    if (slab_) {
        free(slab_);
        slab_ = nullptr;
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
        attr.rnr_retry     = 3;
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

    log_->info("QP → RTS — ready to receive RDMA WRITEs");

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
// runThread — CQ polling loop (zero-copy)
// ---------------------------------------------------------------------------
void rpr::Server::runThread(std::weak_ptr<int> lockPtr) {
    while (!lockPtr.expired()) continue;

    log_->logThreadId();
    log_->info("RoCEv2 receive thread started");

    rogue::GilRelease noGil;   // Release GIL for the entire thread;
                               //  sendFrame() re-acquires via ScopedGil when
                               //  calling Python slaves.

    struct ibv_wc wc;

    // The poll loop body is wrapped in try/catch so that an ibverbs failure
    // (postRecvWr throws rogue::GeneralError on ibv_post_recv failure)
    // shuts the thread down cleanly instead of escaping the thread entry
    // point and triggering std::terminate.
    try {
        while (threadEn_.load()) {
            int n = ibv_poll_cq(cq_, 1, &wc);
            if (n == 0) {
                std::this_thread::sleep_for(std::chrono::microseconds(100));
                continue;
            }
            if (n < 0) {
                log_->warning("ibv_poll_cq error");
                continue;
            }

            uint32_t slot = static_cast<uint32_t>(wc.wr_id);

            // Defensive: every posted WR sets wr_id = slot with slot <
            // numBufs_; a corrupted wr_id must not be dereferenced as a
            // slab offset at line `slab_ + slot * bufSize_` below.  We
            // cannot safely re-post either (the real slot is unknown),
            // so drop the completion and keep polling.
            if (slot >= numBufs_) {
                log_->warning("CQ returned out-of-range wr_id=%" PRIu64
                              " (numBufs=%u); discarding",
                              static_cast<uint64_t>(wc.wr_id), numBufs_);
                continue;
            }

            if (wc.status != IBV_WC_SUCCESS) {
                log_->warning("CQ error: %s (slot=%u)",
                              ibv_wc_status_str(wc.status), slot);

                if (wc.status == IBV_WC_WR_FLUSH_ERR) {
                    // QP transitioned to ERROR; every remaining posted
                    // WR flushes with this status.  Do NOT re-post - stop the
                    // thread gracefully.
                    log_->error("QP in ERROR state (WR_FLUSH_ERR); exiting CQ poll thread");
                    threadEn_.store(false);
                    break;
                }

                postRecvWr(slot);
                continue;
            }

            if (wc.opcode != IBV_WC_RECV_RDMA_WITH_IMM) {
                log_->warning("Unexpected opcode %d (slot=%u), re-posting",
                              wc.opcode, slot);
                postRecvWr(slot);
                continue;
            }

            // Decode immediate value: bits [7:0] = channel id
            uint8_t  channel    = static_cast<uint8_t>(wc.imm_data & 0xFF);
            uint32_t payloadLen = wc.byte_len;

            if (payloadLen == 0 || payloadLen > bufSize_) {
                log_->warning("Bad payload len=%u (slot=%u), re-posting",
                              payloadLen, slot);
                postRecvWr(slot);
                continue;
            }

            // Zero-copy: wrap the slab slot directly as a rogue Buffer.
            // retBuffer() re-posts the slot when downstream releases it.
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

            log_->debug("RX slot=%u channel=%u len=%u", slot, channel, payloadLen);

            sendFrame(frame);

            frameCount_.fetch_add(1, std::memory_order_relaxed);
            byteCount_.fetch_add(payloadLen, std::memory_order_relaxed);
        }
    } catch (const rogue::GeneralError& e) {
        log_->error("RoCEv2 receive thread exiting on ibverbs error: %s", e.what());
        threadEn_.store(false);
    } catch (const std::exception& e) {
        log_->error("RoCEv2 receive thread exiting on exception: %s", e.what());
        threadEn_.store(false);
    } catch (...) {
        log_->error("RoCEv2 receive thread exiting on unknown exception");
        threadEn_.store(false);
    }

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
