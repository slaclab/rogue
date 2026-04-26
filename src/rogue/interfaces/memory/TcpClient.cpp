/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Memory Client Network Bridge
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

#include "rogue/interfaces/memory/TcpClient.h"

#include <inttypes.h>
#include <zmq.h>

#include <cstring>
#include <memory>
#include <string>
#include <chrono>

#include "rogue/GeneralError.h"
#include "rogue/GilRelease.h"
#include "rogue/Logging.h"
#include "rogue/interfaces/memory/Constants.h"
#include "rogue/interfaces/memory/Transaction.h"
#include "rogue/interfaces/memory/TransactionLock.h"

namespace rim = rogue::interfaces::memory;

#ifndef NO_PYTHON
    #include <boost/python.hpp>
namespace bp = boost::python;
#endif

namespace {
static constexpr double DefaultReadyTimeout = 10.0;
static constexpr double DefaultReadyPeriod  = 0.1;
}  // namespace

//! Class creation
rim::TcpClientPtr rim::TcpClient::create(std::string addr, uint16_t port, bool waitReady) {
    rim::TcpClientPtr r = std::make_shared<rim::TcpClient>(addr, port, waitReady);
    return (r);
}

//! Creator
rim::TcpClient::TcpClient(std::string addr, uint16_t port, bool waitReady) : rim::Slave(4, 0xFFFFFFFF) {
    int32_t opt;
    std::string logstr;

    logstr = "memory.TcpClient.";
    logstr.append(addr);
    logstr.append(".");
    logstr.append(std::to_string(port));

    this->bridgeLog_ = rogue::Logging::create(logstr);
    this->probeSeq_ = 0;
    this->probeId_ = 0;
    this->probeDone_ = false;
    this->probeResult_.clear();
    this->waitReadyOnStart_ = waitReady;

    // Format address
    this->respAddr_ = "tcp://";
    this->respAddr_.append(addr);
    this->respAddr_.append(":");
    this->reqAddr_ = this->respAddr_;

    this->zmqCtx_  = zmq_ctx_new();
    this->zmqResp_ = zmq_socket(this->zmqCtx_, ZMQ_PULL);
    this->zmqReq_  = zmq_socket(this->zmqCtx_, ZMQ_PUSH);

    // Throws before threadEn_=true skip the dtor's stop(); free the context here.
    try {
        // Don't buffer when no connection
        opt = 1;
        if (zmq_setsockopt(this->zmqReq_, ZMQ_IMMEDIATE, &opt, sizeof(int32_t)) != 0)
            throw(rogue::GeneralError("memory::TcpClient::TcpClient", "Failed to set socket immediate"));

        this->respAddr_.append(std::to_string(static_cast<int64_t>(port + 1)));
        this->reqAddr_.append(std::to_string(static_cast<int64_t>(port)));

        this->bridgeLog_->debug("Creating response client port: %s", this->respAddr_.c_str());

        opt = 0;
        if (zmq_setsockopt(this->zmqResp_, ZMQ_LINGER, &opt, sizeof(int32_t)) != 0)
            throw(rogue::GeneralError("memory::TcpClient::TcpClient", "Failed to set socket linger"));

        if (zmq_setsockopt(this->zmqReq_, ZMQ_LINGER, &opt, sizeof(int32_t)) != 0)
            throw(rogue::GeneralError("memory::TcpClient::TcpClient", "Failed to set socket linger"));

        opt = 100;
        if (zmq_setsockopt(this->zmqResp_, ZMQ_RCVTIMEO, &opt, sizeof(int32_t)) != 0)
            throw(rogue::GeneralError("memory::TcpClient::TcpClient", "Failed to set socket receive timeout"));

        if (zmq_connect(this->zmqResp_, this->respAddr_.c_str()) < 0)
            throw(rogue::GeneralError::create("memory::TcpClient::TcpClient",
                                              "Failed to connect to remote port %" PRIu16 " at address %s",
                                              port + 1,
                                              addr.c_str()));

        this->bridgeLog_->debug("Creating request client port: %s", this->reqAddr_.c_str());

        if (zmq_connect(this->zmqReq_, this->reqAddr_.c_str()) < 0)
            throw(rogue::GeneralError::create("memory::TcpClient::TcpClient",
                                              "Failed to connect to remote port %" PRIu16 " at address %s",
                                              port,
                                              addr.c_str()));

        // Start rx thread
        threadEn_     = true;
        this->thread_ = new std::thread(&rim::TcpClient::runThread, this);

        // Set a thread name
#ifndef __MACH__
        pthread_setname_np(thread_->native_handle(), "TcpClient");
#endif
    } catch (...) {
        // ~std::thread on a joinable thread calls std::terminate(); join first.
        // RCVTIMEO=100 was already set on zmqResp_ above so the worker exits
        // within ~100 ms of threadEn_=false.
        threadEn_ = false;
        if (thread_ != nullptr) {
            thread_->join();
            delete thread_;
            thread_ = nullptr;
        }
        if (zmqResp_ != nullptr) {
            zmq_close(zmqResp_);
            zmqResp_ = nullptr;
        }
        if (zmqReq_ != nullptr) {
            zmq_close(zmqReq_);
            zmqReq_ = nullptr;
        }
        if (zmqCtx_ != nullptr) {
            zmq_ctx_destroy(zmqCtx_);
            zmqCtx_ = nullptr;
        }
        throw;
    }
}

//! Destructor
rim::TcpClient::~TcpClient() {
    this->stop();
}

// deprecated
void rim::TcpClient::close() {
    this->stop();
}

void rim::TcpClient::stop() {
    if (threadEn_) {
        rogue::GilRelease noGil;
        threadEn_ = false;
        thread_->join();
        delete thread_;
        thread_ = nullptr;
        zmq_close(this->zmqResp_);
        zmqResp_ = nullptr;
        zmq_close(this->zmqReq_);
        zmqReq_ = nullptr;
        zmq_ctx_destroy(this->zmqCtx_);
        zmqCtx_ = nullptr;
    }
}

bool rim::TcpClient::waitReady(double timeout, double period) {
    uint32_t id;
    uint64_t addr = 0;
    uint32_t size = 0;
    uint32_t type = rim::TcpBridgeProbe;
    zmq_msg_t msg[4];
    auto deadline = std::chrono::steady_clock::now() + std::chrono::duration<double>(timeout);

    // Retry the probe until the overall timeout expires. This verifies the
    // full request/response bridge path, not just local socket setup.
    while (std::chrono::steady_clock::now() < deadline) {
        {
            std::lock_guard<std::mutex> probeLock(probeMtx_);
            // Track the current probe ID so the response thread can match the
            // incoming bridge reply back to this wait operation.
            probeId_ = ++probeSeq_;
            probeDone_ = false;
            probeResult_.clear();
            id = probeId_;
        }

        // Build a minimal internal bridge-control request. The server handles
        // this locally and responds with the normal six-part completion
        // message, but without touching downstream memory.
        zmq_msg_init_size(&(msg[0]), 4);
        std::memcpy(zmq_msg_data(&(msg[0])), &id, 4);
        zmq_msg_init_size(&(msg[1]), 8);
        std::memcpy(zmq_msg_data(&(msg[1])), &addr, 8);
        zmq_msg_init_size(&(msg[2]), 4);
        std::memcpy(zmq_msg_data(&(msg[2])), &size, 4);
        zmq_msg_init_size(&(msg[3]), 4);
        std::memcpy(zmq_msg_data(&(msg[3])), &type, 4);

        {
            std::lock_guard<std::mutex> block(bridgeMtx_);
            // Send through the same request socket and multipart framing used
            // by normal memory transactions so this exercises the real bridge
            // path end-to-end.
            for (uint32_t x = 0; x < 4; ++x) {
                if (zmq_sendmsg(this->zmqReq_, &(msg[x]), (x == 3 ? 0 : ZMQ_SNDMORE) | ZMQ_DONTWAIT) < 0) {
                    bridgeLog_->debug("Readiness probe send failed for port %s", this->reqAddr_.c_str());
                    break;
                }
            }
        }

        for (uint32_t x = 0; x < 4; ++x) zmq_msg_close(&(msg[x]));

        std::unique_lock<std::mutex> probeLock(probeMtx_);
        // The receive thread sets probeDone_/probeResult_ when it sees a probe
        // response with the matching ID. We only wait for one retry period
        // here so we can re-send if the server is not up yet.
        probeCond_.wait_for(probeLock, std::chrono::duration<double>(period), [&]() { return probeDone_ && probeId_ == id; });

        if (probeDone_ && probeId_ == id && probeResult_ == "OK") {
            bridgeLog_->debug("Readiness probe succeeded for port %s", this->reqAddr_.c_str());
            return true;
        }
    }

    bridgeLog_->warning("Timed out waiting for bridge readiness on port %s", this->reqAddr_.c_str());
    return false;
}

void rim::TcpClient::start() {
    if (!waitReadyOnStart_) return;

    if (!waitReady(DefaultReadyTimeout, DefaultReadyPeriod)) {
        throw(rogue::GeneralError::create("memory::TcpClient::start",
                                          "Timed out waiting for remote TcpServer readiness on %s",
                                          this->reqAddr_.c_str()));
    }
}

//! Post a transaction
void rim::TcpClient::doTransaction(rim::TransactionPtr tran) {
    uint32_t x;
    uint32_t msgCnt;
    zmq_msg_t msg[5];
    uint32_t id;
    uint64_t addr;
    uint32_t size;
    uint32_t type;

    rogue::GilRelease noGil;
    std::lock_guard<std::mutex> block(bridgeMtx_);
    rim::TransactionLockPtr lock = tran->lock();

    // ID message
    id = tran->id();
    zmq_msg_init_size(&(msg[0]), 4);
    std::memcpy(zmq_msg_data(&(msg[0])), &id, 4);

    // Addr message
    addr = tran->address();
    zmq_msg_init_size(&(msg[1]), 8);
    std::memcpy(zmq_msg_data(&(msg[1])), &addr, 8);

    // Size message
    size = tran->size();
    zmq_msg_init_size(&(msg[2]), 4);
    std::memcpy(zmq_msg_data(&(msg[2])), &size, 4);

    // Type message
    type = tran->type();
    zmq_msg_init_size(&(msg[3]), 4);
    std::memcpy(zmq_msg_data(&(msg[3])), &type, 4);

    // Write transaction
    if (type == rim::Write || type == rim::Post) {
        msgCnt = 5;
        zmq_msg_init_size(&(msg[4]), size);
        std::memcpy(zmq_msg_data(&(msg[4])), tran->begin(), size);

        // Read transaction
    } else {
        msgCnt = 4;
    }

    bridgeLog_->debug("Requested transaction id=%" PRIu32 ", addr=0x%" PRIx64 ", size=%" PRIu32 ", type=%" PRIu32
                      ", cnt=%" PRIu32 ", port: %s",
                      id,
                      addr,
                      size,
                      type,
                      msgCnt,
                      this->reqAddr_.c_str());

    // Add transaction
    if (type == rim::Post)
        tran->done();
    else
        addTransaction(tran);

    // Send message
    for (x = 0; x < msgCnt; x++) {
        if (zmq_sendmsg(this->zmqReq_, &(msg[x]), ((x == (msgCnt - 1) ? 0 : ZMQ_SNDMORE)) | ZMQ_DONTWAIT) < 0) {
            bridgeLog_->warning("Failed to send transaction %" PRIu32 ", msg %" PRIu32 " on %s: %s",
                                id,
                                x,
                                this->reqAddr_.c_str(),
                                zmq_strerror(zmq_errno()));
        }
    }
}

//! Run thread
void rim::TcpClient::runThread() {
    rim::TransactionPtr tran;
    bool err;
    uint64_t more;
    size_t moreSize;
    uint32_t x;
    uint32_t msgCnt;
    zmq_msg_t msg[6];
    uint32_t id;
    uint64_t addr;
    uint32_t size;
    uint32_t type;
    char result[1000];

    bridgeLog_->logThreadId();

    while (threadEn_) {
        for (x = 0; x < 6; x++) zmq_msg_init(&(msg[x]));
        msgCnt = 0;
        x      = 0;

        // Get message
        do {
            // Get the message
            if (zmq_recvmsg(this->zmqResp_, &(msg[x]), 0) >= 0) {
                if (x != 5) x++;
                msgCnt++;

                // Is there more data?
                more     = 0;
                moreSize = 8;
                zmq_getsockopt(this->zmqResp_, ZMQ_RCVMORE, &more, &moreSize);
            } else {
                more = 1;
            }
        } while (threadEn_ && more);

        // Proper message received
        if (threadEn_ && (msgCnt == 6)) {
            // Check sizes
            if ((zmq_msg_size(&(msg[0])) != 4) || (zmq_msg_size(&(msg[1])) != 8) || (zmq_msg_size(&(msg[2])) != 4) ||
                (zmq_msg_size(&(msg[3])) != 4) || (zmq_msg_size(&(msg[5])) > 999)) {
                bridgeLog_->warning(
                    "Bad message sizes. id=%zu addr=%zu size=%zu type=%zu result=%zu",
                    zmq_msg_size(&(msg[0])),
                    zmq_msg_size(&(msg[1])),
                    zmq_msg_size(&(msg[2])),
                    zmq_msg_size(&(msg[3])),
                    zmq_msg_size(&(msg[5])));
                for (x = 0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
                continue;  // while (1)
            }

            // Get return fields
            std::memcpy(&id, zmq_msg_data(&(msg[0])), 4);
            std::memcpy(&addr, zmq_msg_data(&(msg[1])), 8);
            std::memcpy(&size, zmq_msg_data(&(msg[2])), 4);
            std::memcpy(&type, zmq_msg_data(&(msg[3])), 4);

            memset(result, 0, 1000);
            std::strncpy(result, reinterpret_cast<char*>(zmq_msg_data(&(msg[5]))), zmq_msg_size(&(msg[5])));

            if (type == rim::TcpBridgeProbe) {
                std::lock_guard<std::mutex> probeLock(probeMtx_);
                if (id == probeId_) {
                    probeResult_ = result;
                    probeDone_   = true;
                    probeCond_.notify_all();
                }
                for (x = 0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
                continue;  // while (1)
            }

            // Find Transaction
            if ((tran = getTransaction(id)) == NULL) {
                bridgeLog_->warning("Failed to find transaction id=%" PRIu32, id);
                for (x = 0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
                continue;  // while (1)
            }

            // Lock transaction
            rim::TransactionLockPtr lock = tran->lock();

            // Transaction expired
            if (tran->expired()) {
                bridgeLog_->warning("Transaction expired. Id=%" PRIu32, id);
                for (x = 0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
                continue;  // while (1)
            }

            // Double check transaction
            if ((addr != tran->address()) || (size != tran->size()) || (type != tran->type())) {
                bridgeLog_->warning("Transaction data mismatch. Id=%" PRIu32, id);
                tran->error("Transaction data mismatch in TcpClient");
                for (x = 0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
                continue;  // while (1)
            }

            // Copy data if read
            if (type != rim::Write) {
                if (zmq_msg_size(&(msg[4])) != size) {
                    bridgeLog_->warning("Transaction size mismatch. Id=%" PRIu32, id);
                    tran->error("Received transaction response did not match header size");
                    for (x = 0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
                    continue;  // while (1)
                }
                std::memcpy(tran->begin(), zmq_msg_data(&(msg[4])), size);
            }
            if (strcmp(result, "OK") != 0)
                tran->error(result);
            else
                tran->done();
            bridgeLog_->debug("Response for transaction id=%" PRIu32 ", addr=0x%" PRIx64 ", size=%" PRIu32
                              ", type=%" PRIu32 ", cnt=%" PRIu32 ", port: %s, Result: (%s)",
                              id,
                              addr,
                              size,
                              type,
                              msgCnt,
                              this->respAddr_.c_str(),
                              result);
        }
        for (x = 0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
    }
}

void rim::TcpClient::setup_python() {
#ifndef NO_PYTHON

    bp::class_<rim::TcpClient, rim::TcpClientPtr, bp::bases<rim::Slave>, boost::noncopyable>(
        "TcpClient",
        bp::init<std::string, uint16_t, bp::optional<bool> >())
        .def("close", &rim::TcpClient::close)
        .def("waitReady", &rim::TcpClient::waitReady)
        .def("_start", &rim::TcpClient::start);

    bp::implicitly_convertible<rim::TcpClientPtr, rim::SlavePtr>();
#endif
}
