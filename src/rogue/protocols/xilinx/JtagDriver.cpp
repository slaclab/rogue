//-----------------------------------------------------------------------------
// Title      : JTAG Support
//-----------------------------------------------------------------------------
// Company    : SLAC National Accelerator Laboratory
//-----------------------------------------------------------------------------
// Description: JtagDriver.cpp
//-----------------------------------------------------------------------------
// This file is part of 'SLAC Firmware Standard Library'.
// It is subject to the license terms in the LICENSE.txt file found in the
// top-level directory of this distribution and at:
//    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
// No part of 'SLAC Firmware Standard Library', including this file,
// may be copied, modified, propagated, or distributed except according to
// the terms contained in the LICENSE.txt file.
//-----------------------------------------------------------------------------

#include "rogue/Directives.h"

#include "rogue/protocols/xilinx/JtagDriver.h"

#include <arpa/inet.h>
#include <dlfcn.h>
#include <math.h>
#include <netinet/in.h>
#include <pthread.h>
#include <sys/socket.h>

#include <string>

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
      drop_(0),
      done_(false),
      drEn_(false),
      wordSize_(sizeof(Header)),
      memDepth_(1),
      retry_(10),
      log_(nullptr),
      periodNs_(UNKNOWN_PERIOD) {
    // start out with an initial header size; it might be increased
    // once we contacted the server...
    bufSz_ = 2048;
    txBuf_.reserve(bufSz_);
    hdBuf_.reserve(hdBufMax());
    hdBuf_.resize(hdBufMax());  // fill with zeros

    // Create logger
    log_ = rogue::Logging::create("xilinx.jtag");
}

rpx::JtagDriver::Header rpx::JtagDriver::newXid() {
    if (XID_ANY == ++xid_) ++xid_;

    return ((Header)(xid_)) << XID_SHIFT;
}

rpx::JtagDriver::Xid rpx::JtagDriver::getXid(Header x) {
    return (x >> 20) & 0xff;
}

uint32_t rpx::JtagDriver::getCmd(Header x) {
    return x & CMD_MASK;
}

unsigned rpx::JtagDriver::getErr(Header x) {
    if (getCmd(x) != CMD_E) return 0;

    return (x & ERR_MASK) >> ERR_SHIFT;
}

unsigned long rpx::JtagDriver::getLen(Header x) {
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
            return "Unsupported Command";
        case ERR_NOT_PRESENT:
            return "XVC Support not Instantiated in Firmware";
        default:
            break;
    }
    return NULL;
}

rpx::JtagDriver::Header rpx::JtagDriver::mkQuery() {
    return PVERS | CMD_Q | XID_ANY;
}

rpx::JtagDriver::Header rpx::JtagDriver::mkShift(unsigned len) {
    len = len - 1;
    return PVERS | CMD_S | newXid() | (len << LEN_SHIFT);
}

unsigned rpx::JtagDriver::wordSize(Header reply) {
    return (reply & 0x0000000f) + 1;
}

unsigned rpx::JtagDriver::memDepth(Header reply) {
    return (reply >> 4) & 0xffff;
}

uint32_t rpx::JtagDriver::cvtPerNs(Header reply) {
    unsigned rawVal = (reply >> XID_SHIFT) & 0xff;
    double tmp;

    if (0 == rawVal) {
        return UNKNOWN_PERIOD;
    }

    tmp = ((double)rawVal) * 4.0 / 256.0;

    return (uint32_t)round(pow(10.0, tmp) * 1.0E9 / REF_FREQ_HZ());
}

unsigned rpx::JtagDriver::getWordSize() {
    return wordSize_;
}

unsigned rpx::JtagDriver::getMemDepth() {
    return memDepth_;
}

rpx::JtagDriver::Header rpx::JtagDriver::getHdr(uint8_t* buf) {
    Header hdr;
    memcpy(&hdr, buf, sizeof(hdr));
    if (!isLE()) {
        hdr = ntohl(hdr);
    }
    return hdr;
}

void rpx::JtagDriver::setHdr(uint8_t* buf, Header hdr) {
    unsigned empty = getWordSize() - sizeof(hdr);

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
    unsigned attempt;
    unsigned e;
    int got;

    for (attempt = 0; attempt <= retry_; attempt++) {
        // Check if thread should exit
        if (this->done_) break;

        // Start data transfer with retry and timeout
        Header hdr;
        try {
            got = xfer(txb, txBytes, &hdBuf_[0], getWordSize(), rxb, sizeBytes);
            hdr = getHdr(&hdBuf_[0]);

            if ((e = getErr(hdr))) {
                char errb[256];
                const char* msg = getMsg(e);
                int pos;

                pos = snprintf(errb, sizeof(errb), "Got error response from server -- ");

                if (msg)
                    snprintf(errb + pos, sizeof(errb) - pos, "%s", msg);
                else
                    snprintf(errb + pos, sizeof(errb) - pos, "error %d", e);

                throw(rogue::GeneralError::create("JtagDriver::xferRel()", "Protocol error"));
            }
            if (xid == XID_ANY || xid == getXid(hdr)) {
                if (phdr) {
                    *phdr = hdr;
                }
                return got;
            }
        } catch (rogue::GeneralError&) {}
    }
    if (!this->done_) throw(rogue::GeneralError::create("JtagDriver::xferRel()", "Timeout error"));

    return (0);
}

unsigned long rpx::JtagDriver::query() {
    Header hdr;
    unsigned siz;

    setHdr(&txBuf_[0], mkQuery());

    xferRel(&txBuf_[0], getWordSize(), &hdr, nullptr, 0);
    wordSize_ = wordSize(hdr);

    if (wordSize_ < sizeof(hdr)) {
        log_->debug("Encountered an error. Please ensure the board is powered up.\n");
        throw(rogue::GeneralError::create("JtagDriver::query()",
                                          "Received invalid word size. Please ensure the board is powered up.\n"));
    }

    memDepth_ = memDepth(hdr);
    periodNs_ = cvtPerNs(hdr);

    log_->debug("Query result: wordSize %" PRId32 ", memDepth %" PRId32 ", period %l" PRId32 "ns\n",
                wordSize_,
                memDepth_,
                (unsigned long)periodNs_);

    if (0 == memDepth_)
        retry_ = 0;
    else
        retry_ = 10;

    if ((siz = (2 * memDepth_ + 1) * wordSize_) > bufSz_) {
        bufSz_ = siz;
        txBuf_.reserve(bufSz_);
    }

    return memDepth_ * wordSize_;
}

uint32_t rpx::JtagDriver::getPeriodNs() {
    return periodNs_;
}

uint32_t rpx::JtagDriver::setPeriodNs(uint32_t requestedPeriod) {
    uint32_t currentPeriod = getPeriodNs();

    if (0 == requestedPeriod) return currentPeriod;

    return UNKNOWN_PERIOD == currentPeriod ? requestedPeriod : currentPeriod;
}

void rpx::JtagDriver::sendVectors(unsigned long bits, uint8_t* tms, uint8_t* tdi, uint8_t* tdo) {
    unsigned wsz            = getWordSize();
    unsigned long bytesCeil = (bits + 8 - 1) / 8;
    unsigned wholeWords     = bytesCeil / wsz;
    unsigned wholeWordBytes = wholeWords * wsz;
    unsigned wordCeilBytes  = ((bytesCeil + wsz - 1) / wsz) * wsz;
    unsigned idx;
    unsigned bytesLeft = bytesCeil - wholeWordBytes;
    unsigned bytesTot  = wsz + 2 * wordCeilBytes;

    uint8_t* wp;

    log_->debug("sendVec -- bits %l" PRId32 ", bytes %l" PRId32 ", bytesTot %" PRId32 "\n", bits, bytesCeil, bytesTot);

    setHdr(&txBuf_[0], mkShift(bits));

    // reformat
    wp = &txBuf_[0] + wsz;  // past header

    // store sequence of TMS/TDI pairs; word-by-word
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
    xferRel(&txBuf_[0], bytesTot, nullptr, tdo, bytesCeil);
}

void rpx::JtagDriver::dumpInfo(FILE* f) {
    fprintf(f, "Word size:                  %d\n", getWordSize());
    fprintf(f, "Target Memory Depth (bytes) %d\n", getWordSize() * getMemDepth());
    fprintf(f, "Max. Vector Length  (bytes) %ld\n", getMaxVectorSize());
    fprintf(f, "TCK Period             (ns) %ld\n", (unsigned long)getPeriodNs());
}

void rpx::JtagDriver::setup_python() {
#ifndef NO_PYTHON

    bp::class_<rpx::JtagDriver, rpx::JtagDriverPtr, boost::noncopyable>("JtagDriver", bp::init<uint16_t>());
#endif
}
