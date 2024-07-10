/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 *      JTAG Support
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

#ifndef __ROGUE_PROTOCOLS_XILINX_JTAG_DRIVER_H__
#define __ROGUE_PROTOCOLS_XILINX_JTAG_DRIVER_H__

#include "rogue/Directives.h"

#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include <exception>
#include <memory>
#include <stdexcept>
#include <vector>

#include "rogue/GeneralError.h"
#include "rogue/Logging.h"

using std::vector;

namespace rogue {
namespace protocols {
namespace xilinx {
// Driver for the AxisToJtag FW module; a transport-level
// driver must derive from this and implement
//
//   - 'xfer()'.
//   - 'getMaxVectorSize()'
//
// 'getMaxVectorSize()' must return the max. size of a single
// JTAG vector (in bytes) the driver can support. Note that the
// max. *message* size is bigger - it comprises two vectors and
// a header word (depends on the word size the target FW was
// built for).
// E.g., A UDP transport might want to limit to less than the
// ethernet MTU. See xvcDrvUdp.cc for an example...
//
// 'xfer()' must transmit the (opaque) message in 'txb' of size
// 'txBytes' (which is guaranteed to be at most
//
//     2*maxVectorSize() + getWordSize()
//
// The method must then receive the reply from the target
// and:
//   - store the first 'hsize' bytes into 'hbuf'. If less than
//     'hsize' were received then 'xfer' must throw and exception.
//   - store the remainder of the message up to at most 'size'
//     bytes into 'rbuf'.
//   - return the number of actual bytes stored in 'rbuf'.
//
// If a timeout occurs then 'xfer' must throw a TimeoutErr().
//
class JtagDriver {
  protected:
    //! Remote port number
    uint16_t port_;

    // occasionally drop a packet for testing (when enabled)
    bool drEn_;
    bool done_;
    unsigned drop_;

    typedef uint32_t Header;
    typedef uint8_t Xid;

    static const Xid XID_ANY = 0;

    // Log
    std::shared_ptr<rogue::Logging> log_;

  private:
    unsigned wordSize_;
    unsigned memDepth_;

    vector<uint8_t> txBuf_;
    vector<uint8_t> hdBuf_;

    unsigned bufSz_;
    unsigned retry_;

    Xid xid_;

    uint32_t periodNs_;

    Header newXid();

    Header mkQuery();
    Header mkShift(unsigned len);

    virtual void setHdr(uint8_t* buf, Header hdr);

  protected:
    static Header getHdr(uint8_t* buf);

    static const Header PVERS = 0x00000000;
    static const Header CMD_Q = 0x00000000;
    static const Header CMD_S = 0x10000000;
    static const Header CMD_E = 0x20000000;

    static const Header CMD_MASK    = 0x30000000;
    static const unsigned ERR_SHIFT = 0;
    static const Header ERR_MASK    = 0x000000ff;

    static const unsigned XID_SHIFT = 20;
    static const unsigned LEN_SHIFT = 0;
    static const Header LEN_MASK    = 0x000fffff;

    static const unsigned ERR_BAD_VERSION = 1;
    static const unsigned ERR_BAD_COMMAND = 2;
    static const unsigned ERR_TRUNCATED   = 3;
    static const unsigned ERR_NOT_PRESENT = 4;

    static Xid getXid(Header x);
    static uint32_t getCmd(Header x);
    static unsigned getErr(Header x);
    static uint64_t getLen(Header x);

    // returns error message or NULL (unknown error)
    static const char* getMsg(unsigned error);

    // extract from message header
    unsigned wordSize(Header reply);
    unsigned memDepth(Header reply);
    uint32_t cvtPerNs(Header reply);

    static int isLE() {
        static const union {
            uint8_t c[2];
            uint16_t s;
        } u = {.s = 1};
        return !!u.c[0];
    }

    static const uint32_t UNKNOWN_PERIOD = 0;

    static double REF_FREQ_HZ() {
        return 200.0E6;
    }

    // obtain (current/cached) parameters; these may
    // depend on values provided by the transport-level driver
    virtual unsigned getWordSize();
    virtual unsigned getMemDepth();
    virtual uint32_t getPeriodNs();

  public:
    //! Class creation
    static std::shared_ptr<rogue::protocols::xilinx::JtagDriver> create(uint16_t port);

    //! Setup class in python
    static void setup_python();

    explicit JtagDriver(uint16_t port);

    // initialization after full construction
    virtual void init();

    // virtual method to be implemented by transport-level driver;
    // transmit txBytes from TX buffer (txb) and receive 'hsize' header
    // bytes into hdbuf and up to 'size' bytes into rxb.
    // RETURNS: number of payload bytes (w/o header).
    virtual int xfer(uint8_t* txb, unsigned txBytes, uint8_t* hdbuf, unsigned hsize, uint8_t* rxb, unsigned size) {
        return 0;
    }

    // Transfer with retry/timeout.
    // 'txBytes' are transmitted from the TX buffer 'txb'.
    // The message header is received into '*phdr', payload (of up to 'sizeBytes') into 'rxb'.
    //
    virtual int xferRel(uint8_t* txb, unsigned txBytes, Header* phdr, uint8_t* rxb, unsigned sizeBytes);

    // XVC query support; return the size of max. supported JTAG vector in bytes
    //                    if 0 then no the target does not have memory and if
    //                    there is reliable transport there is no limit to vector
    //                    length.
    virtual uint64_t query();

    // Max. vector size (in bytes) this driver supports - may be different
    // from what the target supports and the minimum will be used...
    // Note that this is a single vector (the message the driver
    // must handle typically contains two vectors and a header, so
    // the driver must consider this when computing the max. supported
    // vector size)
    virtual uint64_t getMaxVectorSize() {
        return 0;
    }

    virtual uint32_t setPeriodNs(uint32_t newPeriod);

    // send tms and tdi vectors of length numBits (each) and receive tdo
    // little-endian (first send/received at lowest offset)
    virtual void sendVectors(uint64_t numBits, uint8_t* tms, uint8_t* tdi, uint8_t* tdo);

    virtual void dumpInfo(FILE* f = stdout);

    // Return 'done_' flag
    bool isDone() {
        return this->done_;
    }
};

static unsigned hdBufMax() {
    return 16;
}

// Convenience
typedef std::shared_ptr<rogue::protocols::xilinx::JtagDriver> JtagDriverPtr;
}  // namespace xilinx
}  // namespace protocols
}  // namespace rogue

#endif
