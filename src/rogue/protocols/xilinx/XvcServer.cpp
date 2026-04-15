/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 *
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

#include "rogue/protocols/xilinx/XvcServer.h"

#include "rogue/GilRelease.h"

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <unistd.h>

#include <atomic>
#include <cerrno>
#include <cstdint>
#include <cstring>

#include "rogue/protocols/xilinx/XvcConnection.h"

namespace rpx = rogue::protocols::xilinx;

rpx::XvcServer::XvcServer(uint16_t port, int wakeFd, JtagDriver* drv, unsigned maxMsgSize)
    : sd_(-1),
      wakeFd_(wakeFd),
      drv_(drv),
      maxMsgSize_(maxMsgSize),
      port_(port) {
    struct sockaddr_in a{};
    int yes = 1;

    a.sin_family      = AF_INET;
    a.sin_addr.s_addr = INADDR_ANY;
    a.sin_port        = htons(port);

    if ((sd_ = ::socket(AF_INET, SOCK_STREAM, 0)) < 0)
        throw(rogue::GeneralError::create("XvcServer::XvcServer()", "Failed to create socket"));

    if (::setsockopt(sd_, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes))) {
        ::close(sd_);
        sd_ = -1;
        throw(rogue::GeneralError::create("XvcServer::XvcServer()", "setsockopt(SO_REUSEADDR) failed"));
    }

    if (::bind(sd_, reinterpret_cast<struct sockaddr*>(&a), sizeof(a))) {
        ::close(sd_);
        sd_ = -1;
        throw(rogue::GeneralError::create("XvcServer::XvcServer()", "Unable to bind Stream socket to local address"));
    }

    // Resolve kernel-assigned port when caller asked for 0.
    if (port_ == 0) {
        socklen_t len = sizeof(a);
        if (::getsockname(sd_, reinterpret_cast<struct sockaddr*>(&a), &len) < 0) {
            ::close(sd_);
            sd_ = -1;
            throw(rogue::GeneralError::create("XvcServer::XvcServer()", "getsockname failed"));
        }
        port_ = ntohs(a.sin_port);
    }

    if (::listen(sd_, 1)) {
        ::close(sd_);
        sd_ = -1;
        throw(rogue::GeneralError::create("XvcServer::XvcServer()", "Unable to listen on socket"));
    }
}

rpx::XvcServer::~XvcServer() {
    if (sd_ >= 0) ::close(sd_);
}

uint32_t rpx::XvcServer::getPort() const {
    return static_cast<uint32_t>(port_);
}

void rpx::XvcServer::run(std::atomic<bool>& threadEn, rogue::LoggingPtr log) {
    if (sd_ < 0 || sd_ >= FD_SETSIZE || (wakeFd_ >= 0 && wakeFd_ >= FD_SETSIZE)) {
        int badFd = (sd_ < 0 || sd_ >= FD_SETSIZE) ? sd_ : wakeFd_;
        throw(rogue::GeneralError::create("XvcServer::run()", "fd %d invalid or exceeds FD_SETSIZE (%d)",
                                          badFd, FD_SETSIZE));
    }
    fd_set rset;
    int maxFd = sd_ + 1;
    if (wakeFd_ >= 0 && wakeFd_ >= sd_) maxFd = wakeFd_ + 1;

    while (threadEn.load(std::memory_order_acquire)) {
        FD_ZERO(&rset);
        FD_SET(sd_, &rset);
        if (wakeFd_ >= 0) FD_SET(wakeFd_, &rset);

        // NO timeout — block until accept-ready OR wakefd readable.
        // Release the GIL across the blocking select() so that the outer
        // rogue::ScopedGil held by Xvc::runThread (needed for tstate identity
        // under nested Master::sendFrame callbacks into Python ris.Slave
        // subclasses) does not starve Python worker threads.
        int nready;
        {
            rogue::GilRelease noGil;
            nready = ::select(maxFd, &rset, nullptr, nullptr, nullptr);
        }
        if (nready < 0) {
            if (errno == EINTR) continue;
            int savedErrno = errno;
            log->warning("XvcServer::run(): select() failed: %s (errno %d)", strerror(savedErrno), savedErrno);
            throw(rogue::GeneralError::create("XvcServer::run()", "select() failed: %s (errno %d)",
                                              strerror(savedErrno), savedErrno));
        }
        if (wakeFd_ >= 0 && FD_ISSET(wakeFd_, &rset)) {
            // Shutdown signaled by Xvc::stop(); break out of loop.
            break;
        }
        if (FD_ISSET(sd_, &rset)) {
            try {
                // Forward the wake-fd so readTo() inside the connection
                // wakes promptly on shutdown.
                XvcConnection conn(sd_, wakeFd_, drv_, maxMsgSize_);
                conn.run();
            } catch (rogue::GeneralError& e) {
                log->debug("Sub-connection closed: %s", e.what());
            }
        }
    }
}
