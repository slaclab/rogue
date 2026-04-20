/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 *    JtagDriver.cpp
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

#include "rogue/protocols/xilinx/JtagDriver.h"

#include <arpa/inet.h>

#include <cinttypes>
#include <climits>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <memory>

namespace rpx = rogue::protocols::xilinx;

#ifndef NO_PYTHON
    #include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Class creation
rpx::JtagDriverPtr rpx::JtagDriver::create(uint16_t port) {
    // Create shared_ptr
    rpx::JtagDriverPtr r = std::make_shared<rpx::JtagDriver>(port);
    return (r);
}

rpx::JtagDriver::JtagDriver(uint16_t port)
    : port_(port),
      drEn_(false),
      done_{false},
      drop_(0),
      log_(nullptr),
      wordSize_(sizeof(Header)),
      memDepth_(1),
      bufSz_(2048),
      retry_(10),
      xid_(0),
      periodNs_(UNKNOWN_PERIOD) {
    // start out with an initial header size; it might be increased
    // once we contacted the server...
    txBuf_.resize(bufSz_);
    hdBuf_.resize(hdBufMax());

    // Create logger
    log_ = rogue::Logging::create("xilinx.jtag");
}

rpx::JtagDriver::Header rpx::JtagDriver::newXid() {
    if (XID_ANY == ++xid_) ++xid_;

    return (static_cast<Header>(xid_)) << XID_SHIFT;
}

rpx::JtagDriver::Xid rpx::JtagDriver::getXid(Header x) {
    return static_cast<Xid>((x >> 20) & 0xff);
}

uint32_t rpx::JtagDriver::getCmd(Header x) {
    return x & CMD_MASK;
}

unsigned rpx::JtagDriver::getErr(Header x) {
    if (getCmd(x) != CMD_E) return 0;

    return (x & ERR_MASK) >> ERR_SHIFT;
}

uint64_t rpx::JtagDriver::getLen(Header x) {
    if (getCmd(x) != CMD_S)
        throw(
            rogue::GeneralError::create("JtagDriver::getLen()", "Cannot extract length from non-shift command header"));

    return ((x & LEN_MASK) >> LEN_SHIFT) + 1;
}

const char* rpx::JtagDriver::getMsg(unsigned e) {
    switch (e) {
        case 0:
            return "NO ERROR";
        case ERR_BAD_VERSION:
            return "Unsupported Protocol Version";
        case ERR_BAD_COMMAND:
            return "Unsupported Command";
        case ERR_TRUNCATED:
            return "Truncated Message";
        case ERR_NOT_PRESENT:
            return "XVC Support not Instantiated in Firmware";
        default:
            break;
    }
    return nullptr;
}

rpx::JtagDriver::Header rpx::JtagDriver::mkQuery() {
    return PVERS | CMD_Q | XID_ANY;
}

rpx::JtagDriver::Header rpx::JtagDriver::mkShift(unsigned len) {
    if (len == 0)
        throw(rogue::GeneralError::create("JtagDriver::mkShift()", "shift length must be > 0"));
    len = len - 1;
    return PVERS | CMD_S | newXid() | ((len & LEN_MASK) << LEN_SHIFT);
}

unsigned rpx::JtagDriver::wordSize(Header reply) {
    return (reply & 0x0000000f) + 1;
}

unsigned rpx::JtagDriver::memDepth(Header reply) {
    return (reply >> 4) & 0xffff;
}

uint32_t rpx::JtagDriver::cvtPerNs(Header reply) {
    unsigned rawVal = (reply >> XID_SHIFT) & 0xff;

    if (0 == rawVal) {
        return UNKNOWN_PERIOD;
    }

    double tmp = static_cast<double>(rawVal) * 4.0 / 256.0;

    return static_cast<uint32_t>(std::round(std::pow(10.0, tmp) * 1.0E9 / REF_FREQ_HZ()));
}

unsigned rpx::JtagDriver::getWordSize() {
    return wordSize_;
}

unsigned rpx::JtagDriver::getMemDepth() {
    return memDepth_;
}

rpx::JtagDriver::Header rpx::JtagDriver::getHdr(const uint8_t* buf) {
    Header hdr{};
    memcpy(&hdr, buf, sizeof(hdr));
    if (!isLE()) {
        hdr = ntohl(hdr);
    }
    return hdr;
}

void rpx::JtagDriver::setHdr(uint8_t* buf, Header hdr) {
    unsigned ws = getWordSize();
    if (static_cast<size_t>(ws) < sizeof(hdr))
        throw(rogue::GeneralError::create("JtagDriver::setHdr()", "wordSize %u < header size %zu", ws, sizeof(hdr)));
    unsigned empty = ws - static_cast<unsigned>(sizeof(hdr));

    if (!isLE()) {
        hdr = ntohl(hdr);  // just use for byte-swap
    }
    memcpy(buf, &hdr, sizeof(hdr));
    memset(buf + sizeof(hdr), 0, empty);
}

void rpx::JtagDriver::init() {
    // obtain server parameters
    query();
}

int rpx::JtagDriver::xferRel(uint8_t* txb, unsigned txBytes, Header* phdr, uint8_t* rxb, unsigned sizeBytes) {
    Xid xid = getXid(getHdr(txb));
    int got = 0;

    for (unsigned attempt = 0; attempt <= retry_; attempt++) {
        // Check if thread should exit
        if (this->done_.load(std::memory_order_acquire)) break;

        // Start data transfer with retry and timeout
        Header hdr{};
        try {
            got = xfer(txb, txBytes, &hdBuf_[0], getWordSize(), rxb, sizeBytes);
            hdr = getHdr(&hdBuf_[0]);

            unsigned e = getErr(hdr);
            if (e) {
                char errb[256];
                const char* msg = getMsg(e);

                int pos = snprintf(errb, sizeof(errb), "Got error response from server -- ");
                if (pos < 0) pos = 0;
                if (static_cast<size_t>(pos) >= sizeof(errb)) pos = static_cast<int>(sizeof(errb) - 1);
                size_t remaining = sizeof(errb) - static_cast<size_t>(pos);

                if (msg)
                    snprintf(errb + pos, remaining, "%s", msg);
                else
                    snprintf(errb + pos, remaining, "error %u", e);

                throw(rogue::GeneralError::create("JtagDriver::xferRel()", "%s", errb));
            }
            if (xid == XID_ANY || xid == getXid(hdr)) {
                if (phdr) {
                    *phdr = hdr;
                }
                return got;
            }
        } catch (rogue::GeneralError&) {}
    }
    if (!this->done_.load(std::memory_order_acquire))
        throw(rogue::GeneralError::create("JtagDriver::xferRel()", "Timeout error"));

    return (0);
}

uint64_t rpx::JtagDriver::query() {
    Header hdr{};

    setHdr(&txBuf_[0], mkQuery());

    xferRel(&txBuf_[0], getWordSize(), &hdr, nullptr, 0);
    wordSize_ = wordSize(hdr);

    if (static_cast<size_t>(wordSize_) < sizeof(hdr)) {
        log_->debug("Encountered an error. Please ensure the board is powered up.\n");
        throw(rogue::GeneralError::create("JtagDriver::query()",
                                          "Received invalid word size. Please ensure the board is powered up.\n"));
    }

    memDepth_ = memDepth(hdr);
    periodNs_ = cvtPerNs(hdr);

    log_->debug("Query result: wordSize %u, memDepth %u, period %" PRIu32 " ns\n",
                wordSize_,
                memDepth_,
                periodNs_);

    if (0 == memDepth_)
        retry_ = 0;
    else
        retry_ = 10;

    uint64_t siz64 = (2ULL * static_cast<uint64_t>(memDepth_) + 1) * static_cast<uint64_t>(wordSize_);
    if (siz64 > UINT_MAX)
        throw(rogue::GeneralError::create("JtagDriver::query()", "buffer size overflows unsigned"));
    unsigned siz = static_cast<unsigned>(siz64);
    if (siz > bufSz_) {
        bufSz_ = siz;
        txBuf_.resize(bufSz_);
    }

    return static_cast<uint64_t>(memDepth_) * static_cast<uint64_t>(wordSize_);
}

uint32_t rpx::JtagDriver::getPeriodNs() {
    return periodNs_;
}

uint32_t rpx::JtagDriver::setPeriodNs(uint32_t requestedPeriod) {
    uint32_t currentPeriod = getPeriodNs();

    if (0 == requestedPeriod) return currentPeriod;

    return UNKNOWN_PERIOD == currentPeriod ? requestedPeriod : currentPeriod;
}

void rpx::JtagDriver::sendVectors(uint64_t bits, uint8_t* tms, uint8_t* tdi, uint8_t* tdo) {
    if (bits == 0 || bits > LEN_MASK + 1)
        throw(rogue::GeneralError::create("JtagDriver::sendVectors()",
              "bit count %" PRIu64 " out of range [1, %u]", bits, static_cast<unsigned>(LEN_MASK + 1)));

    unsigned wsz            = getWordSize();
    uint64_t bytesCeil      = (bits + 7) / 8;
    unsigned wholeWords     = static_cast<unsigned>(bytesCeil / wsz);
    unsigned wholeWordBytes = wholeWords * wsz;
    unsigned wordCeilBytes  = static_cast<unsigned>(((bytesCeil + wsz - 1) / wsz) * wsz);
    unsigned bytesLeft = static_cast<unsigned>(bytesCeil - wholeWordBytes);
    unsigned bytesTot  = wsz + 2 * wordCeilBytes;

    if (bytesTot > bufSz_)
        throw(rogue::GeneralError::create("JtagDriver::sendVectors()",
              "bytesTot %u exceeds buffer size %u", bytesTot, bufSz_));

    log_->debug("sendVec -- bits %" PRIu64 ", bytes %" PRIu64 ", bytesTot %u\n", bits, bytesCeil, bytesTot);

    setHdr(&txBuf_[0], mkShift(static_cast<unsigned>(bits)));

    // reformat
    uint8_t* wp = &txBuf_[0] + wsz;  // past header

    // store sequence of TMS/TDI pairs; word-by-word
    unsigned idx = 0;
    for (idx = 0; idx < wholeWordBytes; idx += wsz) {
        memcpy(wp, &tms[idx], wsz);
        wp += wsz;
        memcpy(wp, &tdi[idx], wsz);
        wp += wsz;
    }
    if (bytesLeft) {
        memcpy(wp, &tms[idx], bytesLeft);
        memcpy(wp + wsz, &tdi[idx], bytesLeft);
    }
    xferRel(&txBuf_[0], bytesTot, nullptr, tdo, static_cast<unsigned>(bytesCeil));
}

void rpx::JtagDriver::dumpInfo(FILE* f) {
    fprintf(f, "Word size:                  %" PRIu64 "\n", static_cast<uint64_t>(getWordSize()));
    fprintf(f,
            "Target Memory Depth (bytes) %" PRIu64 "\n",
            static_cast<uint64_t>(getWordSize()) * static_cast<uint64_t>(getMemDepth()));
    fprintf(f, "Max. Vector Length  (bytes) %" PRIu64 "\n", getMaxVectorSize());
    fprintf(f, "TCK Period             (ns) %" PRIu64 "\n", static_cast<uint64_t>(getPeriodNs()));
}

void rpx::JtagDriver::setup_python() {
#ifndef NO_PYTHON

    bp::class_<rpx::JtagDriver, rpx::JtagDriverPtr, boost::noncopyable>("JtagDriver", bp::init<uint16_t>());
#endif
}
