/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Memory Server Network Bridge
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

#include "rogue/interfaces/memory/TcpServer.h"

#include <inttypes.h>
#include <zmq.h>

#include <cstring>
#include <memory>
#include <string>

#include "rogue/GeneralError.h"
#include "rogue/GilRelease.h"
#include "rogue/Logging.h"
#include "rogue/interfaces/memory/Constants.h"

namespace rim = rogue::interfaces::memory;

#ifndef NO_PYTHON
    #include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Class creation
rim::TcpServerPtr rim::TcpServer::create(std::string addr, uint16_t port) {
    rim::TcpServerPtr r = std::make_shared<rim::TcpServer>(addr, port);
    return (r);
}

//! Creator
rim::TcpServer::TcpServer(std::string addr, uint16_t port) {
    std::string logstr;
    uint32_t opt;

    logstr = "memory.TcpServer.";
    logstr.append(addr);
    logstr.append(".");
    logstr.append(std::to_string(port));

    this->bridgeLog_ = rogue::Logging::create(logstr);

    // Format address
    this->respAddr_ = "tcp://";
    this->respAddr_.append(addr);
    this->respAddr_.append(":");
    this->reqAddr_ = this->respAddr_;

    this->zmqCtx_  = zmq_ctx_new();
    this->zmqResp_ = zmq_socket(this->zmqCtx_, ZMQ_PUSH);
    this->zmqReq_  = zmq_socket(this->zmqCtx_, ZMQ_PULL);

    // Throws before threadEn_=true skip the dtor's stop(); free the context here.
    try {
        this->respAddr_.append(std::to_string(static_cast<int64_t>(port + 1)));
        this->reqAddr_.append(std::to_string(static_cast<int64_t>(port)));

        this->bridgeLog_->debug("Creating response client port: %s", this->respAddr_.c_str());

        opt = 0;
        if (zmq_setsockopt(this->zmqResp_, ZMQ_LINGER, &opt, sizeof(int32_t)) != 0)
            throw(rogue::GeneralError("memory::TcpServer::TcpServer", "Failed to set socket linger"));

        if (zmq_setsockopt(this->zmqReq_, ZMQ_LINGER, &opt, sizeof(int32_t)) != 0)
            throw(rogue::GeneralError("memory::TcpServer::TcpServer", "Failed to set socket linger"));

        opt = 100;
        if (zmq_setsockopt(this->zmqReq_, ZMQ_RCVTIMEO, &opt, sizeof(int32_t)) != 0)
            throw(rogue::GeneralError("memory::TcpServer::TcpServer", "Failed to set socket receive timeout"));

        if (zmq_bind(this->zmqResp_, this->respAddr_.c_str()) < 0)
            throw(rogue::GeneralError::create("memory::TcpServer::TcpServer",
                                              "Failed to bind server to port %" PRIu16
                                              " at address %s, another process may be using this port",
                                              port + 1,
                                              addr.c_str()));

        this->bridgeLog_->debug("Creating request client port: %s", this->reqAddr_.c_str());

        if (zmq_bind(this->zmqReq_, this->reqAddr_.c_str()) < 0)
            throw(rogue::GeneralError::create("memory::TcpServer::TcpServer",
                                              "Failed to bind server to port %" PRIu16
                                              " at address %s, another process may be using this port",
                                              port,
                                              addr.c_str()));

        this->bridgeLog_->debug("TCP memory bridge ready. request=%s response=%s",
                                this->reqAddr_.c_str(),
                                this->respAddr_.c_str());

        threadEn_     = true;
        this->thread_ = std::make_unique<std::thread>(&rim::TcpServer::runThread, this);

        // Set a thread name
#ifndef __MACH__
        pthread_setname_np(thread_->native_handle(), "TcpServer");
#endif
    } catch (...) {
        // ~std::thread on a joinable thread calls std::terminate(); join first.
        // RCVTIMEO=100 was already set on zmqReq_ above so the worker exits
        // within ~100 ms of threadEn_=false. Release the GIL around join() to
        // match stop(): the worker may be blocked acquiring the GIL to deliver
        // a transaction into Python, and joining while holding the GIL would
        // deadlock.
        threadEn_ = false;
        if (thread_) {
            {
                rogue::GilRelease noGil;
                thread_->join();
            }
            thread_.reset();
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
rim::TcpServer::~TcpServer() {
    this->stop();
}

void rim::TcpServer::close() {
    this->stop();
}

void rim::TcpServer::start() {
    // The bridge is fully bound and the worker thread is already running by
    // the time the constructor returns. This hook exists for managed-lifecycle
    // symmetry with TcpClient.
}

int rim::TcpServer::sendResponseMsg_(void* msg, int flags) {
    return zmq_sendmsg(this->zmqResp_, reinterpret_cast<zmq_msg_t*>(msg), flags);
}

void rim::TcpServer::stop() {
    if (threadEn_) {
        rogue::GilRelease noGil;
        threadEn_ = false;
        thread_->join();
        thread_.reset();
        this->bridgeLog_->debug("Stopping TCP memory bridge. request=%s response=%s",
                                this->reqAddr_.c_str(),
                                this->respAddr_.c_str());
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
    }
}

//! Run thread
void rim::TcpServer::runThread() {
    uint8_t* data;
    uint64_t more;
    size_t moreSize;
    uint32_t x;
    uint32_t msgCnt;
    zmq_msg_t msg[6];
    uint32_t id;
    uint64_t addr;
    uint32_t size;
    uint32_t type;
    std::string result;

    bridgeLog_->logThreadId();

    while (threadEn_) {
        for (x = 0; x < 6; x++) zmq_msg_init(&(msg[x]));
        msgCnt = 0;
        x      = 0;

        // Get message
        do {
            // Get the message
            if (zmq_recvmsg(this->zmqReq_, &(msg[x]), 0) >= 0) {
                if (x != 4) x++;
                msgCnt++;

                // Is there more data?
                more     = 0;
                moreSize = 8;
                zmq_getsockopt(this->zmqReq_, ZMQ_RCVMORE, &more, &moreSize);
            } else {
                more = 1;
            }
        } while (threadEn_ && more);

        // Proper message received
        if (threadEn_ && (msgCnt == 4 || msgCnt == 5)) {
            // Check sizes
            if ((zmq_msg_size(&(msg[0])) != 4) || (zmq_msg_size(&(msg[1])) != 8) || (zmq_msg_size(&(msg[2])) != 4) ||
                (zmq_msg_size(&(msg[3])) != 4)) {
                bridgeLog_->warning(
                    "Bad message sizes. id=%zu addr=%zu size=%zu type=%zu",
                    zmq_msg_size(&(msg[0])),
                    zmq_msg_size(&(msg[1])),
                    zmq_msg_size(&(msg[2])),
                    zmq_msg_size(&(msg[3])));
                for (x = 0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
                continue;  // while (1)
            }

            // Get return fields
            std::memcpy(&id, zmq_msg_data(&(msg[0])), 4);
            std::memcpy(&addr, zmq_msg_data(&(msg[1])), 8);
            std::memcpy(&size, zmq_msg_data(&(msg[2])), 4);
            std::memcpy(&type, zmq_msg_data(&(msg[3])), 4);

            // Bridge readiness probe is handled locally.
            if (type == rim::TcpBridgeProbe) {
                if ((msgCnt != 4) || (size != 0)) {
                    bridgeLog_->warning("Malformed readiness probe. Id=%" PRIu32, id);
                    for (x = 0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
                    continue;  // while (1)
                }
                zmq_msg_init_size(&(msg[4]), 0);
                result = "OK";

            // Write data is expected
            } else if ((type == rim::Write) || (type == rim::Post)) {
                if ((msgCnt != 5) || (zmq_msg_size(&(msg[4])) != size)) {
                    bridgeLog_->warning("Transaction write data error. Id=%" PRIu32, id);
                    for (x = 0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
                    continue;  // while (1)
                }
            } else {
                zmq_msg_init_size(&(msg[4]), size);
            }

            if (type != rim::TcpBridgeProbe) {
                // Data pointer
                data = reinterpret_cast<uint8_t*>(zmq_msg_data(&(msg[4])));

                bridgeLog_->debug("Starting transaction id=%" PRIu32 ", addr=0x%" PRIx64 ", size=%" PRIu32
                                  ", type=%" PRIu32,
                                  id,
                                  addr,
                                  size,
                                  type);

                // Execute transaction and wait for result
                this->clearError();
                reqTransaction(addr, size, data, type);
                waitTransaction(0);
                result = getError();

                bridgeLog_->debug("Done transaction id=%" PRIu32 ", addr=0x%" PRIx64 ", size=%" PRIu32
                                  ", type=%" PRIu32 ", result=(%s)",
                                  id,
                                  addr,
                                  size,
                                  type,
                                  result.c_str());
            }

            // Result message, at least one char needs to be sent
            if (result.length() == 0) result = "OK";
            if (zmq_msg_init_size(&(msg[5]), result.length()) < 0) {
                bridgeLog_->warning("zmq_msg_init_size failed for result (%" PRIu32 " bytes): %s",
                                    static_cast<uint32_t>(result.length()), zmq_strerror(zmq_errno()));
                for (x = 0; x < 5; x++) zmq_msg_close(&(msg[x]));
                continue;
            }
            std::memcpy(zmq_msg_data(&(msg[5])), result.c_str(), result.length());

            uint32_t sendFailed = 0;
            for (x = 0; x < 6; x++) {
                if (this->sendResponseMsg_(&(msg[x]), (x == 5) ? 0 : ZMQ_SNDMORE) < 0) {
                    bridgeLog_->warning("zmq_sendmsg failed on part %" PRIu32 " for id=%" PRIu32 ": %s",
                                        x, id, zmq_strerror(zmq_errno()));
                    sendFailed = 1;
                    zmq_msg_close(&(msg[x]));
                    for (uint32_t y = x + 1; y < 6; y++) zmq_msg_close(&(msg[y]));
                    break;
                }
            }
            if (sendFailed) {
                bridgeLog_->error("Multi-part reply for id=%" PRIu32
                                  " failed mid-stream on part %" PRIu32
                                  "; peer may have received a torso-only response. "
                                  "Resetting response socket to clear PUSH multipart FSM.",
                                  id, x);

                // Rebuild response socket to reset multipart FSM.
                if (this->zmqResp_ != nullptr) {
                    if (zmq_unbind(this->zmqResp_, this->respAddr_.c_str()) != 0) {
                        bridgeLog_->warning("Failed to unbind response socket from %s during recovery: %s",
                                            this->respAddr_.c_str(), zmq_strerror(zmq_errno()));
                    }
                    zmq_close(this->zmqResp_);
                    this->zmqResp_ = nullptr;
                }

                this->zmqResp_ = zmq_socket(this->zmqCtx_, ZMQ_PUSH);
                bool rebuilt = (this->zmqResp_ != nullptr);

                if (rebuilt) {
                    int32_t lopt = 0;
                    if (zmq_setsockopt(this->zmqResp_, ZMQ_LINGER, &lopt, sizeof(lopt)) != 0) {
                        bridgeLog_->error("Failed to set ZMQ_LINGER on rebuilt response socket: %s",
                                          zmq_strerror(zmq_errno()));
                        rebuilt = false;
                    } else if (zmq_bind(this->zmqResp_, this->respAddr_.c_str()) < 0) {
                        bridgeLog_->error("Failed to rebind response socket to %s: %s",
                                          this->respAddr_.c_str(), zmq_strerror(zmq_errno()));
                        rebuilt = false;
                    }
                }

                if (!rebuilt) {
                    if (this->zmqResp_ != nullptr) {
                        zmq_close(this->zmqResp_);
                        this->zmqResp_ = nullptr;
                    }
                    bridgeLog_->error("Unable to recover TcpServer response socket; "
                                      "exiting bridge worker thread (stop()/dtor will "
                                      "complete teardown)");
                    return;
                }
            }
        } else {
            for (x = 0; x < msgCnt; x++) zmq_msg_close(&(msg[x]));
        }
    }
}

void rim::TcpServer::setup_python() {
#ifndef NO_PYTHON

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wdeprecated-declarations"
    bp::class_<rim::TcpServer, rim::TcpServerPtr, bp::bases<rim::Master>, boost::noncopyable>(
        "TcpServer",
        bp::init<std::string, uint16_t>())
        .def("close", &rim::TcpServer::close)
        .def("_start", &rim::TcpServer::start)
        .def("_stop", &rim::TcpServer::stop);
#pragma GCC diagnostic pop

    bp::implicitly_convertible<rim::TcpServerPtr, rim::MasterPtr>();
#endif
}
