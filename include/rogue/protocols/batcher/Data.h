/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    AXI Batcher Data
 *-----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to
 * the license terms in the LICENSE.txt file found in the top-level directory
 * of this distribution and at:
 * https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
 * No part of the rogue software platform, including this file, may be
 * copied, modified, propagated, or distributed except according to the terms
 * contained in the LICENSE.txt file.
 *-----------------------------------------------------------------------------
 **/
#ifndef __ROGUE_PROTOCOLS_BATCHER_DATA_H__
#define __ROGUE_PROTOCOLS_BATCHER_DATA_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <thread>

#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/FrameIterator.h"

namespace rogue {
namespace protocols {
namespace batcher {

/**
 * @brief Parsed batcher record descriptor.
 *
 * @details
 * `Data` represents one record extracted from a batcher super-frame by
 * `CoreV1` or `CoreV2`. It stores:
 * - Iterators delimiting the payload bytes in the original frame.
 * - Per-record routing/control fields (`dest`, `fUser`, `lUser`).
 *
 * `SplitterV1` and `SplitterV2` consume `Data` objects from `CoreV1/CoreV2`
 * to build and emit individual output frames.
 *
 * Protocol references:
 * - Batcher v1: https://confluence.slac.stanford.edu/x/th1SDg
 * - Batcher v2: https://confluence.slac.stanford.edu/x/L2VlK
 */
class Data {
    // Iterator to beginning of record payload in source frame.
    rogue::interfaces::stream::FrameIterator it_;

    // Record payload size in bytes.
    uint32_t size_;

    // Destination/channel field from record tail.
    uint8_t dest_;

    // First-user metadata byte from record tail.
    uint8_t fUser_;

    // Last-user metadata byte from record tail.
    uint8_t lUser_;

  public:
    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Creates a parsed record descriptor.
     * @param it Iterator to beginning of record payload.
     * @param size Record payload size in bytes.
     * @param dest Destination/channel field.
     * @param fUser First-user metadata byte.
     * @param lUser Last-user metadata byte.
     * @return Shared pointer to the created record descriptor.
     */
    static std::shared_ptr<rogue::protocols::batcher::Data> create(rogue::interfaces::stream::FrameIterator it,
                                                                   uint32_t size,
                                                                   uint8_t dest,
                                                                   uint8_t fUser,
                                                                   uint8_t lUser);

    /**
     * @brief Constructs a parsed record descriptor.
     * @param it Iterator to beginning of record payload.
     * @param size Record payload size in bytes.
     * @param dest Destination/channel field.
     * @param fUser First-user metadata byte.
     * @param lUser Last-user metadata byte.
     */
    Data(rogue::interfaces::stream::FrameIterator it, uint32_t size, uint8_t dest, uint8_t fUser, uint8_t lUser);

    /** @brief Destroys the record descriptor. */
    ~Data();

    /**
     * @brief Returns iterator to beginning of payload.
     * @return Payload-begin iterator.
     */
    rogue::interfaces::stream::FrameIterator begin();

    /**
     * @brief Returns iterator to end of payload.
     * @return Payload-end iterator.
     */
    rogue::interfaces::stream::FrameIterator end();

    /**
     * @brief Returns payload size.
     * @return Payload size in bytes.
     */
    uint32_t size();

    /**
     * @brief Returns destination/channel value.
     * @return Destination/channel field.
     */
    uint8_t dest();

    /**
     * @brief Returns first-user metadata.
     * @return First-user byte.
     */
    uint8_t fUser();

    /**
     * @brief Returns last-user metadata.
     * @return Last-user byte.
     */
    uint8_t lUser();
};

// Convienence
typedef std::shared_ptr<rogue::protocols::batcher::Data> DataPtr;
}  // namespace batcher
}  // namespace protocols
}  // namespace rogue
#endif
