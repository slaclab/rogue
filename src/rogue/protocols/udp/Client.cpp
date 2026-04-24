/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * UDP Client
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

#include "rogue/protocols/udp/Client.h"

#include <inttypes.h>
#include <arpa/inet.h>
#include <unistd.h>

#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <string>

#include "rogue/GeneralError.h"
#include "rogue/GilRelease.h"
#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Buffer.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/FrameLock.h"
#include "rogue/protocols/udp/Core.h"

namespace rpu = rogue::protocols::udp;
namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
    #include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Class creation
rpu::ClientPtr rpu::Client::create(std::string host, uint16_t port, bool jumbo) {
    rpu::ClientPtr r = std::make_shared<rpu::Client>(host, port, jumbo);
    return (r);
}

//! Creator
rpu::Client::Client(std::string host, uint16_t port, bool jumbo) : rpu::Core(jumbo) {
    struct addrinfo aiHints;
    struct addrinfo* aiList = 0;
    const sockaddr_in* addr;
    int32_t val;
    int32_t ret;
    uint32_t size;

    address_ = host;
    port_    = port;
    udpLog_  = rogue::Logging::create("udp.Client");

    // Create a shared pointer to use as a lock for runThread()
    std::shared_ptr<int> scopePtr = std::make_shared<int>(0);

    // Create socket
    if ((fd_ = socket(AF_INET, SOCK_DGRAM, 0)) < 0)
        throw(rogue::GeneralError::create("Client::Client",
                                          "Failed to create socket for port %" PRIu16 " at address %s",
                                          port_,
                                          address_.c_str()));

    // Lookup host address
    bzero(&aiHints, sizeof(aiHints));
    aiHints.ai_flags    = AI_CANONNAME;
    aiHints.ai_family   = AF_INET;
    aiHints.ai_socktype = SOCK_DGRAM;
    aiHints.ai_protocol = IPPROTO_UDP;

    if (::getaddrinfo(address_.c_str(), 0, &aiHints, &aiList) || !aiList)
        throw(rogue::GeneralError::create("Client::Client", "Failed to resolve address %s", address_.c_str()));

    addr = (const sockaddr_in*)(aiList->ai_addr);

    // Setup Remote Address
    memset(&remAddr_, 0, sizeof(struct sockaddr_in));
    ((struct sockaddr_in*)(&remAddr_))->sin_family      = AF_INET;
    ((struct sockaddr_in*)(&remAddr_))->sin_addr.s_addr = addr->sin_addr.s_addr;
    ((struct sockaddr_in*)(&remAddr_))->sin_port        = htons(port_);

    // Fixed size buffer pool
    setFixedSize(maxPayload());
    setPoolSize(10000);  // Initial value, 10K frames

    // Start rx thread
    threadEn_ = true;
    thread_   = new std::thread(&rpu::Client::runThread, this, std::weak_ptr<int>(scopePtr));

    udpLog_->debug("UDP client ready. remote=%s:%" PRIu16 ", maxPayload=%" PRIu32,
                   address_.c_str(),
                   port_,
                   maxPayload());

    // Set a thread name
#ifndef __MACH__
    pthread_setname_np(thread_->native_handle(), "UdpClient");
#endif
}

//! Destructor
rpu::Client::~Client() {
    this->stop();
}

void rpu::Client::stop() {
    if (threadEn_) {
        threadEn_ = false;
        // Release GIL before join so the worker can safely enter any Python path; shutdown(SHUT_RDWR)
        // wakes the blocking recvfrom() in runThread() so join() can observe threadEn_=false and exit
        // cleanly (PROTO-UDP-001 part 2; mirrors Fifo::~Fifo() precedent, PR #1191 b1a669c96).
        rogue::GilRelease noGil;
        ::shutdown(fd_, SHUT_RDWR);
        thread_->join();
        delete thread_;
        thread_ = nullptr;
        udpLog_->debug("Stopping UDP client for remote %s:%" PRIu16, address_.c_str(), port_);

        ::close(fd_);
    }
}

//! Accept a frame from master
void rpu::Client::acceptFrame(ris::FramePtr frame) {
    ris::Frame::BufferIterator it;
    int32_t res;
    fd_set fds;
    struct timeval tout;
    uint32_t x;
    struct msghdr msg;
    struct iovec msg_iov[1];

    // Setup message header
    msg.msg_name       = &remAddr_;
    msg.msg_namelen    = sizeof(struct sockaddr_in);
    msg.msg_iov        = msg_iov;
    msg.msg_iovlen     = 1;
    msg.msg_control    = NULL;
    msg.msg_controllen = 0;
    msg.msg_flags      = 0;

    rogue::GilRelease noGil;
    ris::FrameLockPtr frLock = frame->lock();
    std::lock_guard<std::mutex> lock(udpMtx_);

    // Drop errored frames
    if (frame->getError()) {
        udpLog_->warning("Dropping errored outbound frame. remote=%s:%" PRIu16 ", error=0x%" PRIx8,
                         address_.c_str(),
                         port_,
                         frame->getError());
        return;
    }

    // Go through each buffer in the frame
    for (it = frame->beginBuffer(); it != frame->endBuffer(); ++it) {
        if ((*it)->getPayload() == 0) break;

        // Setup IOVs
        msg_iov[0].iov_base = (*it)->begin();
        msg_iov[0].iov_len  = (*it)->getPayload();

        // Keep trying since select call can fire
        // but write fails because we did not win the (*it)er lock
        do {
            // Setup fds for select call
            FD_ZERO(&fds);
            FD_SET(fd_, &fds);

            // Setup select timeout
            tout = timeout_;

            if (select(fd_ + 1, NULL, &fds, NULL, &tout) <= 0) {
                udpLog_->critical("Client::acceptFrame: Timeout waiting for outbound transmit after %" PRIu32
                                  ".%" PRIu32 " seconds! May be caused by outbound backpressure.",
                                  timeout_.tv_sec,
                                  timeout_.tv_usec);
                res = 0;
            } else if ((res = sendmsg(fd_, &msg, 0)) < 0) {
                udpLog_->warning("UDP write call failed for %s: %s", address_.c_str(), std::strerror(errno));
            }
        } while (res == 0);  // Continue while write result was zero
    }
}

//! Run thread
void rpu::Client::runThread(std::weak_ptr<int> lockPtr) {
    ris::BufferPtr buff;
    ris::FramePtr frame;
    fd_set fds;
    int32_t res;
    struct timeval tout;
    uint32_t avail;

    // Wait until constructor completes
    while (!lockPtr.expired()) continue;

    udpLog_->logThreadId();

    // Preallocate frame
    frame = reqLocalFrame(maxPayload(), false);

    while (threadEn_) {
        // Attempt receive
        buff  = *(frame->beginBuffer());
        avail = buff->getAvailable();
        res   = recvfrom(fd_, buff->begin(), avail, MSG_TRUNC, NULL, 0);

        if (res > 0) {
            // Message was too big
            if (res > avail) {
                udpLog_->warning("Receive data was too large. remote=%s:%" PRIu16 ", rx=%i, avail=%" PRIu32
                                 ". Dropping.",
                                 address_.c_str(),
                                 port_,
                                 res,
                                 avail);
            } else {
                buff->setPayload(res);
                sendFrame(frame);
            }

            // Get new frame
            frame = reqLocalFrame(maxPayload(), false);
        } else {
            // Setup fds for select call
            FD_ZERO(&fds);
            FD_SET(fd_, &fds);

            // Setup select timeout
            tout.tv_sec  = 0;
            tout.tv_usec = 100;

            // Select returns with available buffer
            select(fd_ + 1, &fds, NULL, NULL, &tout);
        }
    }
}

void rpu::Client::setup_python() {
#ifndef NO_PYTHON

    bp::class_<rpu::Client, rpu::ClientPtr, bp::bases<rpu::Core, ris::Master, ris::Slave>, boost::noncopyable>(
        "Client",
        bp::init<std::string, uint16_t, bool>());

    bp::implicitly_convertible<rpu::ClientPtr, rpu::CorePtr>();
    bp::implicitly_convertible<rpu::ClientPtr, ris::MasterPtr>();
    bp::implicitly_convertible<rpu::ClientPtr, ris::SlavePtr>();
#endif
}
