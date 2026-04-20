/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 *    JTAG support
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

#include "rogue/protocols/xilinx/XvcConnection.h"

#include "rogue/GilRelease.h"

#include <netinet/tcp.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cerrno>
#include <cinttypes>
#include <cstdio>
#include <cstring>

namespace rpx = rogue::protocols::xilinx;

rpx::XvcConnection::XvcConnection(int sd, int wakeFd, JtagDriver* drv, uint64_t maxVecLen)
    : sd_(-1),
      wakeFd_(wakeFd),
      drv_(drv),
      maxVecLen_(maxVecLen),
      supVecLen_(0),
      lastErrno_(0) {
    socklen_t sz = sizeof(peer_);

    // RAII for the sd_
    if ((sd_ = ::accept(sd, reinterpret_cast<struct sockaddr*>(&peer_), &sz)) < 0)
        throw(rogue::GeneralError::create("XvcConnection::XvcConnection()", "Unable to accept connection"));

    // XVC protocol is synchronous / not pipelined :-(
    // use TCP_NODELAY to make sure our messages (many of which
    // are small) are sent ASAP
    int yes = 1;
    if (setsockopt(sd_, IPPROTO_TCP, TCP_NODELAY, &yes, sizeof(yes))) {
        ::close(sd_);
        sd_ = -1;
        throw(rogue::GeneralError::create("XvcConnection::XvcConnection()", "Unable to set TCP_NODELAY"));
    }

#if defined(__APPLE__) && defined(SO_NOSIGPIPE)
    // macOS fallback: no MSG_NOSIGNAL on BSD send(); use per-socket
    // SO_NOSIGPIPE instead so writes to a closed peer surface EPIPE rather
    // than SIGPIPE-ing the process.
    int nosigpipe = 1;
    if (setsockopt(sd_, SOL_SOCKET, SO_NOSIGPIPE, &nosigpipe, sizeof(nosigpipe))) {
        ::close(sd_);
        sd_ = -1;
        throw(rogue::GeneralError::create("XvcConnection::XvcConnection()",
                                          "setsockopt(SO_NOSIGPIPE) failed"));
    }
#endif
}

rpx::XvcConnection::~XvcConnection() {
    if (sd_ >= 0) ::close(sd_);
}

ssize_t rpx::XvcConnection::readTo(void* buf, size_t count) {
    if (sd_ < 0 || sd_ >= FD_SETSIZE || (wakeFd_ >= 0 && wakeFd_ >= FD_SETSIZE)) {
        lastErrno_ = EBADF;
        return -2;
    }
    int maxFd = sd_ + 1;
    if (wakeFd_ >= 0 && wakeFd_ >= sd_) maxFd = wakeFd_ + 1;

    // NO timeout — block until data, EOF, or shutdown signal.
    // Release the GIL across the blocking select() so that the outer
    // rogue::ScopedGil held by Xvc::runThread does not starve Python worker
    // threads while this connection is parked waiting for client bytes.
    // Retry on EINTR (matches XvcServer::run): a benign signal must not tear
    // down the client connection.
    int nready;
    fd_set rset;
    while (true) {
        FD_ZERO(&rset);
        FD_SET(sd_, &rset);
        if (wakeFd_ >= 0) FD_SET(wakeFd_, &rset);
        {
            rogue::GilRelease noGil;
            nready = ::select(maxFd, &rset, nullptr, nullptr, nullptr);
        }
        if (nready >= 0) break;
        if (errno == EINTR) continue;
        lastErrno_ = errno;
        return -2;  // unrecoverable select error
    }
    if (wakeFd_ >= 0 && FD_ISSET(wakeFd_, &rset)) {
        return -1;  // shutdown requested via self-pipe
    }
    if (FD_ISSET(sd_, &rset)) {
        ssize_t r;
        do {
            r = ::read(sd_, buf, count);
        } while (r < 0 && errno == EINTR);
        // >0 = bytes; 0 = peer EOF; <0 = socket error (mapped to -2 so
        // callers don't confuse it with the -1 shutdown sentinel).
        if (r < 0) {
            lastErrno_ = errno;
            return -2;
        }
        return r;
    }
    lastErrno_ = ENODATA;
    return -2;  // unexpected: neither wake-fd nor data-fd ready
}

// fill rx buffer to 'n' octets
void rpx::XvcConnection::fill(uint64_t n) {
    uint8_t* p = rp_ + static_cast<ptrdiff_t>(rl_);
    uint64_t k = n;

    if (n <= rl_) return;

    k -= rl_;
    while (k > 0) {
        ssize_t got = readTo(p, static_cast<size_t>(k));

        if (got > 0) {
            k -= static_cast<uint64_t>(got);
            p += got;
            continue;
        }
        if (got == 0) {
            throw(rogue::GeneralError::create("XvcConnection::fill()", "peer closed connection"));
        }
        // got == -1: shutdown requested via wakeFd.
        if (got == -1)
            throw(rogue::GeneralError::create("XvcConnection::fill()", "shutdown requested"));
        // got <= -2: select() or unexpected error.
        throw(rogue::GeneralError::create("XvcConnection::fill()",
              "socket/select error: %s (errno %d)", strerror(lastErrno_), lastErrno_));
    }
    rl_ = n;
}

// mark 'n' octets as 'consumed'
void rpx::XvcConnection::bump(uint64_t n) {
    if (n > rl_)
        throw(rogue::GeneralError::create("XvcConnection::bump()", "consuming %" PRIu64 " bytes but only %" PRIu64 " available", n, rl_));
    rp_ += static_cast<ptrdiff_t>(n);
    rl_ -= n;
    if (rl_ == 0) {
        rp_ = &rxb_[0];
    }
}

void rpx::XvcConnection::allocBufs() {
    uint64_t overhead = 128;  // headers and such;

    // Determine the vector size supported by the target
    uint64_t tgtVecLen = drv_->query();

    if (0 == tgtVecLen) {
        // target can stream
        tgtVecLen = maxVecLen_;
    }

    // What can the driver support?
    supVecLen_ = drv_->getMaxVectorSize();

    if (supVecLen_ == 0) {
        // supports any size
        supVecLen_ = tgtVecLen;
    } else if (tgtVecLen < supVecLen_) {
        supVecLen_ = tgtVecLen;
    }

    chunk_ = (2 * maxVecLen_ + overhead);

    rxb_.resize(static_cast<size_t>(2 * chunk_));
    txb_.resize(static_cast<size_t>(maxVecLen_ + overhead));

    rp_ = &rxb_[0];
    rl_ = 0;
    tl_ = 0;
}

void rpx::XvcConnection::flush() {
    uint8_t* p = &txb_[0];

    while (tl_ > 0) {
        size_t toSend = static_cast<size_t>(tl_);
        ssize_t put;
        do {
#if defined(__APPLE__)
            put = ::send(sd_, p, toSend, 0);
#else
            put = ::send(sd_, p, toSend, MSG_NOSIGNAL);
#endif
        } while (put < 0 && errno == EINTR);
        if (put <= 0) {
            int e = errno;
            throw(rogue::GeneralError::create("XvcConnection::flush()",
                  "send() failed: %s (errno %d)", strerror(e), e));
        }

        p += put;
        tl_ -= static_cast<uint64_t>(put);
    }
}

void rpx::XvcConnection::run() {
    uint32_t bits = 0;
    uint64_t bitsLeft = 0, bitsSent = 0;
    uint64_t bytes = 0;
    uint64_t vecLen = 0;
    uint64_t off = 0;

    allocBufs();

    while (!drv_->isDone()) {
        // read stuff;
        ssize_t got = readTo(rp_, static_cast<size_t>(chunk_));

        if (got == 0) throw(rogue::GeneralError::create("XvcConnection::run()", "peer closed connection"));
        if (got == -1) throw(rogue::GeneralError::create("XvcConnection::run()", "shutdown requested"));
        if (got < 0) throw(rogue::GeneralError::create("XvcConnection::run()",
                     "socket/select error: %s (errno %d)", strerror(lastErrno_), lastErrno_));

        rl_ = static_cast<uint64_t>(got);

        do {
            fill(2);

            if (0 == ::memcmp(rp_, "ge", 2)) {
                fill(8);

                drv_->query();  // informs the driver that there is a new connection

                int slen = snprintf(
                    reinterpret_cast<char*>(&txb_[0]), txb_.size(), "xvcServer_v1.0:%" PRIu64 "\n", maxVecLen_);
                if (slen < 0)
                    throw(rogue::GeneralError::create("XvcConnection::run()", "snprintf failed for getinfo reply"));
                tl_ = (static_cast<uint64_t>(slen) < txb_.size())
                          ? static_cast<uint64_t>(slen)
                          : txb_.size() - 1;

                bump(8);
            } else if (0 == ::memcmp(rp_, "se", 2)) {
                fill(11);

                uint32_t requestedPeriod = (static_cast<uint32_t>(rp_[10]) << 24) |
                                           (static_cast<uint32_t>(rp_[9])  << 16) |
                                           (static_cast<uint32_t>(rp_[8])  <<  8) |
                                            static_cast<uint32_t>(rp_[7]);

                uint32_t newPeriod = drv_->setPeriodNs(requestedPeriod);

                for (size_t u = 0; u < sizeof(newPeriod); u++) {
                    txb_[u]   = static_cast<uint8_t>(newPeriod);
                    newPeriod = newPeriod >> 8;
                }

                tl_ = 4;

                bump(11);
            } else if (0 == ::memcmp(rp_, "sh", 2)) {
                fill(10);

                bits = (static_cast<uint32_t>(rp_[9])  << 24) |
                       (static_cast<uint32_t>(rp_[8])  << 16) |
                       (static_cast<uint32_t>(rp_[7])  <<  8) |
                        static_cast<uint32_t>(rp_[6]);
                bytes = (static_cast<uint64_t>(bits) + 7) / 8;

                if (bytes > maxVecLen_)
                    throw(rogue::GeneralError::create("XvcConnection::run()", "Requested bit vector length too big"));

                bump(10);
                fill(2 * bytes);

                vecLen = bytes > supVecLen_ ? supVecLen_ : bytes;

                if (vecLen == 0)
                    throw(rogue::GeneralError::create("XvcConnection::run()",
                          "supported vector length is zero — cannot chunk shift"));

                // break into chunks the driver can handle; due to the xvc layout we can't efficiently
                // start working on a chunk while still waiting for more data to come in (well - we could
                // but had to have the full TDI vector plus a chunk of the TMS vector in. Thus, we don't
                // bother...).
                for (off = 0, bitsLeft = bits; bitsLeft > 0; bitsLeft -= bitsSent, off += vecLen) {
                    bitsSent = 8 * vecLen;
                    if (bitsLeft < bitsSent) {
                        bitsSent = bitsLeft;
                    }

                    drv_->sendVectors(bitsSent,
                                      rp_ + static_cast<ptrdiff_t>(off),
                                      rp_ + static_cast<ptrdiff_t>(bytes + off),
                                      &txb_[0] + static_cast<ptrdiff_t>(off));
                }
                tl_ = bytes;

                bump(2 * bytes);
            } else {
                throw(rogue::GeneralError::create("XvcConnection::run()", "Unsupported message received"));
            }
            flush();

            /* Repeat until all bytes from the current chunk are exhausted.
             * Most chunks contain a single vector shift message and are
             * consumed in the first iteration. If not, the spill-over area
             * provides room for a second iteration which terminates the loop.
             */
        } while (rl_ > 0);
    }
}
