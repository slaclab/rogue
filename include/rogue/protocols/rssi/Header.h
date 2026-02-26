/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * RSSI header
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
#ifndef __ROGUE_PROTOCOLS_RSSI_HEADER_H__
#define __ROGUE_PROTOCOLS_RSSI_HEADER_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <string>

#include "rogue/interfaces/stream/Frame.h"

namespace rogue {
namespace protocols {
namespace rssi {

/**
 * @brief RSSI header container and codec.
 *
 * @details
 * Wraps a stream frame and provides helpers for encoding, decoding, and
 * validating RSSI header fields.
 *
 * Field model:
 * - Public members are the decoded/encoded RSSI header fields.
 * - `verify()` parses bytes from the frame into these members and validates
 *   checksum/size.
 * - `update()` writes members back to frame bytes and updates checksum.
 * - SYN-only fields are meaningful when `syn == true`.
 */
class Header {
  private:
    // Set 16-bit network-order integer at byte offset.
    inline void setUInt16(uint8_t* data, uint8_t byte, uint16_t value);

    // Get 16-bit network-order integer at byte offset.
    inline uint16_t getUInt16(uint8_t* data, uint8_t byte);

    // Set 32-bit network-order integer at byte offset.
    inline void setUInt32(uint8_t* data, uint8_t byte, uint32_t value);

    // Get 32-bit network-order integer at byte offset.
    inline uint32_t getUInt32(uint8_t* data, uint8_t byte);

    // Compute RSSI checksum over indicated header size.
    uint16_t compSum(uint8_t* data, uint8_t size);

    // Underlying frame carrying RSSI header bytes.
    std::shared_ptr<rogue::interfaces::stream::Frame> frame_;

    // Last transmit/update timestamp.
    struct timeval time_;

    // Number of times update() has been called.
    uint32_t count_;

  public:
    /** @brief Encoded RSSI non-SYN header size in bytes. */
    static const int32_t HeaderSize = 8;

    /** @brief Encoded RSSI SYN header size in bytes. */
    static const uint32_t SynSize   = 24;

    /**
     * @brief Creates a header wrapper for an existing frame.
     * @param frame Frame containing RSSI header bytes.
     * @return Shared pointer to the created header wrapper.
     */
    static std::shared_ptr<rogue::protocols::rssi::Header> create(
        std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    /**
     * @brief Constructs a header wrapper for an existing frame.
     * @param frame Frame containing RSSI header bytes.
     */
    explicit Header(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    /** @brief Destroys the header wrapper. */
    ~Header();

    /**
     * @brief Returns the underlying frame.
     * @return Frame associated with this header object.
     */
    std::shared_ptr<rogue::interfaces::stream::Frame> getFrame();

    /**
     * @brief Verifies header checksum and initializes cached fields.
     * @return True if the header checksum and format are valid.
     */
    bool verify();

    /** @brief Encodes current field values into the frame and updates checksum. */
    void update();

    /**
     * @brief Returns the last transmit timestamp.
     * @return Reference to timestamp associated with this header.
     */
    struct timeval& getTime();

    /**
     * @brief Returns the transmit count.
     * @return Transmit count associated with this header.
     */
    uint32_t count();

    /** @brief Resets transmit timestamp to the current time. */
    void rstTime();

    /**
     * @brief Returns a formatted string of header contents.
     * @return Human-readable header dump.
     */
    std::string dump();

    /** @brief SYN flag (synchronization/header-extension present). */
    bool syn;

    /** @brief ACK flag. */
    bool ack;

    /** @brief RST flag. */
    bool rst;

    /** @brief NUL/keepalive flag. */
    bool nul;

    /** @brief Busy flag. */
    bool busy;

    /** @brief Sequence number field. */
    uint8_t sequence;

    /** @brief Acknowledge number field. */
    uint8_t acknowledge;

    /** @brief Protocol version (SYN headers only). */
    uint8_t version;

    /** @brief CHK capability flag (SYN headers only). */
    bool chk;

    /** @brief Maximum outstanding segments (SYN headers only). */
    uint8_t maxOutstandingSegments;

    /** @brief Maximum segment size (SYN headers only). */
    uint16_t maxSegmentSize;

    /** @brief Retransmission timeout (SYN headers only). */
    uint16_t retransmissionTimeout;

    /** @brief Cumulative ACK timeout (SYN headers only). */
    uint16_t cumulativeAckTimeout;

    /** @brief NULL/keepalive timeout (SYN headers only). */
    uint16_t nullTimeout;

    /** @brief Maximum retransmissions (SYN headers only). */
    uint8_t maxRetransmissions;

    /** @brief Maximum cumulative ACK count (SYN headers only). */
    uint8_t maxCumulativeAck;

    /** @brief Timeout unit field (SYN headers only). */
    uint8_t timeoutUnit;

    /** @brief Connection ID (SYN headers only). */
    uint32_t connectionId;
};

// Convienence
typedef std::shared_ptr<rogue::protocols::rssi::Header> HeaderPtr;

}  // namespace rssi
}  // namespace protocols
};  // namespace rogue

#endif
