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

#include <inttypes.h>
#include <stdint.h>
#include <unistd.h>

#include <cerrno>
#include <cstdio>
#include <cstring>
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
/**
 * @brief Base transport driver for the AxisToJtag firmware protocol.
 *
 * @details
 * `JtagDriver` implements protocol framing, query/shift command handling,
 * retry logic, and vector chunking for XVC/JTAG operations. Concrete transport
 * drivers derive from this class and provide I/O primitives.
 *
 * Transport subclasses must implement:
 * - `xfer()` to move opaque protocol messages to/from the target.
 * - `getMaxVectorSize()` to report maximum JTAG vector bytes supported by the
 *   transport.
 *
 * Message sizing:
 * - Transport receives at most `2 * getMaxVectorSize() + getWordSize()` bytes
 *   in one transfer request.
 * - Protocol messages may contain two vectors plus protocol header.
 *
 * `xfer()` contract:
 * - transmit `txBytes` from `txb`.
 * - receive exactly `hsize` header bytes into `hdbuf` (or throw on short read).
 * - receive up to `size` payload bytes into `rxb`.
 * - return number of payload bytes written to `rxb`.
 * - throw on timeout/error so retry/error handling can be applied by `xferRel()`.
 */
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
    /**
     * @brief Creates a JTAG driver instance.
     *
     * @param port Transport/service port value associated with this driver.
     * @return Shared pointer to the created driver.
     */
    static std::shared_ptr<rogue::protocols::xilinx::JtagDriver> create(uint16_t port);

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Constructs the JTAG driver base state.
     *
     * @param port Transport/service port value associated with this driver.
     */
    explicit JtagDriver(uint16_t port);

    /**
     * @brief Performs post-construction initialization.
     *
     * @details
     * Base implementation performs target query to cache protocol parameters.
     */
    virtual void init();

    /**
     * @brief Transport-level transfer primitive implemented by subclass.
     *
     * @details
     * Sends request bytes and receives reply header/payload for one protocol
     * transaction.
     *
     * @param txb Request transmit buffer.
     * @param txBytes Number of transmit bytes in `txb`.
     * @param hdbuf Reply header destination buffer.
     * @param hsize Number of reply header bytes expected.
     * @param rxb Reply payload destination buffer.
     * @param size Maximum payload bytes to store in `rxb`.
     * @return Number of payload bytes received.
     * @throws rogue::GeneralError On transport/protocol timeout or I/O error.
     */
    virtual int xfer(uint8_t* txb, unsigned txBytes, uint8_t* hdbuf, unsigned hsize, uint8_t* rxb, unsigned size) {
        return 0;
    }

    /**
     * @brief Executes transfer with retry and protocol validation.
     *
     * @details
     * Calls `xfer()` repeatedly up to retry limit, checks header/error fields,
     * validates transaction ID where applicable, and returns payload length.
     *
     * @param txb Request transmit buffer.
     * @param txBytes Number of transmit bytes in `txb`.
     * @param phdr Optional destination for parsed reply header.
     * @param rxb Reply payload destination buffer.
     * @param sizeBytes Maximum payload bytes accepted in `rxb`.
     * @return Number of payload bytes received.
     * @throws rogue::GeneralError If retries are exhausted or protocol errors persist.
     */
    virtual int xferRel(uint8_t* txb, unsigned txBytes, Header* phdr, uint8_t* rxb, unsigned sizeBytes);

    /**
     * @brief Queries target capabilities and caches protocol parameters.
     *
     * @details
     * Updates cached word size, memory depth, and period information.
     * If target reports no memory (`0`), streaming semantics apply.
     *
     * @return Maximum target-supported vector size in bytes (or `0` for streaming target).
     */
    virtual uint64_t query();

    /**
     * @brief Returns transport-supported maximum vector size in bytes.
     *
     * @details
     * This value is transport-specific and may differ from target capability.
     * Effective runtime vector length is bounded by the minimum of transport and
     * target limits.
     *
     * @return Maximum transport-supported vector size in bytes.
     */
    virtual uint64_t getMaxVectorSize() {
        return 0;
    }

    /**
     * @brief Requests update of TCK period.
     *
     * @details
     * Base behavior returns current period when `newPeriod == 0`; otherwise
     * returns requested period if target period is unknown, or current cached
     * period when fixed by target.
     *
     * @param newPeriod Requested period in nanoseconds.
     * @return Effective period in nanoseconds.
     */
    virtual uint32_t setPeriodNs(uint32_t newPeriod);

    /**
     * @brief Sends JTAG TMS/TDI vectors and receives TDO.
     *
     * @details
     * Vectors are interpreted little-endian (first transmitted/received bits at
     * lowest byte offsets). Large vectors are chunked according to target and
     * transport capabilities.
     *
     * @param numBits Number of bits in each input vector.
     * @param tms Pointer to TMS vector bytes.
     * @param tdi Pointer to TDI vector bytes.
     * @param tdo Pointer to output TDO vector bytes.
     */
    virtual void sendVectors(uint64_t numBits, uint8_t* tms, uint8_t* tdi, uint8_t* tdo);

    /**
     * @brief Dumps cached driver/target information.
     *
     * @param f Output stream (`stdout` by default).
     */
    virtual void dumpInfo(FILE* f = stdout);

    /**
     * @brief Returns completion/shutdown flag.
     *
     * @return `true` when driver is marked done; otherwise `false`.
     */
    bool isDone() {
        return this->done_;
    }
};

/** @brief Maximum temporary header buffer size in bytes. */
static unsigned hdBufMax() {
    return 16;
}

// Convenience
typedef std::shared_ptr<rogue::protocols::xilinx::JtagDriver> JtagDriverPtr;
}  // namespace xilinx
}  // namespace protocols
}  // namespace rogue

#endif
