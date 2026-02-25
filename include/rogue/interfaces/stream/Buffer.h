/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Stream frame container
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
#ifndef __ROGUE_INTERFACES_STREAM_BUFFER_H__
#define __ROGUE_INTERFACES_STREAM_BUFFER_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>

#include "rogue/interfaces/stream/Frame.h"

namespace rogue {
namespace interfaces {
namespace stream {

class Pool;
class Frame;

/**
 * @brief Stream frame buffer container.
 *
 * @details
 * Represents a contiguous memory block (allocated by a `Pool`) that contributes to
 * a frame. Buffers reserve header/tail regions for protocol layers. Most users should
 * access payload data through `FrameIterator`; `Buffer` is a lower-level C++ API.
 */
class Buffer {
    // Pointer to entity which allocated this buffer
    std::shared_ptr<rogue::interfaces::stream::Pool> source_;

    // Pointer to frame containing this buffer
    std::weak_ptr<rogue::interfaces::stream::Frame> frame_;

    // Pointer to raw data buffer. Raw pointer is used here!
    uint8_t* data_;

    // Meta data used to track this buffer by source
    uint32_t meta_;

    // Alloc size of buffer, alloc may be greater than raw size due to buffer allocator
    uint32_t allocSize_;

    // Raw size of buffer, size as requested, alloc may be greater
    uint32_t rawSize_;

    // Header room of buffer
    uint32_t headRoom_;

    // Tail room of buffer, used to keep payload from using up tail space
    uint32_t tailRoom_;

    // Data count including header
    uint32_t payload_;

    // Interface specific flags
    uint32_t flags_;

    // Error state
    uint32_t error_;

  public:
    /** @brief Iterator alias for byte-wise buffer access. */
    typedef uint8_t* iterator;

    // Class factory which returns a BufferPtr
    /* Create a new Buffer with associated data.
     *
     * Not exposed to python, Called by Pool class
     * data Pointer to raw data block associated with Buffer
     * meta Meta data to track allocation
     * size Size of raw data block usable by Buffer
     * alloc Total memory allocated, may be greater than size
     */
    static std::shared_ptr<rogue::interfaces::stream::Buffer> create(
        std::shared_ptr<rogue::interfaces::stream::Pool> source,
        void* data,
        uint32_t meta,
        uint32_t size,
        uint32_t alloc);

    // Create a buffer.
    Buffer(std::shared_ptr<rogue::interfaces::stream::Pool> source,
           void* data,
           uint32_t meta,
           uint32_t size,
           uint32_t alloc);

    // Destroy a buffer
    ~Buffer();

    // Set owner frame, called by Frame class only
    void setFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    /**
     * @brief Returns metadata associated with this buffer.
     *
     * @details Metadata is used by `Pool` implementations to track allocations.
     *
     * @return Metadata value.
     */
    uint32_t getMeta();

    /**
     * @brief Sets metadata associated with this buffer.
     *
     * @details Metadata is used by `Pool` implementations to track allocations.
     *
     * @param meta Metadata value.
     */
    void setMeta(uint32_t meta);

    /**
     * @brief Adjusts header reservation size.
     *
     * @param value Header adjustment in bytes.
     */
    void adjustHeader(int32_t value);

    /** @brief Clears header reservation. */
    void zeroHeader();

    /**
     * @brief Adjusts tail reservation size.
     *
     * @param value Tail adjustment in bytes.
     */
    void adjustTail(int32_t value);

    /** @brief Clears tail reservation. */
    void zeroTail();

    /**
     * @brief Returns iterator to start of buffer payload region.
     *
     * @details Excludes reserved header space.
     *
     * @return Begin buffer iterator.
     */
    uint8_t* begin();

    /**
     * @brief Returns iterator to end of usable buffer region.
     *
     * @details Excludes reserved tail space.
     *
     * @return End buffer iterator.
     */
    uint8_t* end();

    /**
     * @brief Returns iterator to end of current payload.
     *
     * @return End payload iterator.
     */
    uint8_t* endPayload();

    /**
     * @brief Returns payload-capable buffer size.
     *
     * @details Full buffer size minus current header/tail reservations.
     *
     * @return Buffer size in bytes.
     */
    uint32_t getSize();

    /**
     * @brief Returns remaining available payload space.
     *
     * @return Available payload space in bytes.
     */
    uint32_t getAvailable();

    /**
     * @brief Returns current payload size.
     *
     * @return Payload size in bytes.
     */
    uint32_t getPayload();

    /**
     * @brief Sets payload size.
     *
     * @param size New payload size in bytes.
     */
    void setPayload(uint32_t size);

    /**
     * @brief Ensures payload size is at least `size`.
     *
     * @details Payload size is unchanged when already larger than `size`.
     *
     * @param size Minimum payload size in bytes.
     */
    void minPayload(uint32_t size);

    /**
     * @brief Adjusts payload size by signed delta.
     *
     * @param value Payload adjustment in bytes.
     */
    void adjustPayload(int32_t value);

    /**
     * @brief Sets payload size to maximum available buffer space.
     *
     * @details Fills buffer minus header and tail reservations.
     */
    void setPayloadFull();

    /** @brief Clears payload (sets payload size to zero). */
    void setPayloadEmpty();

    /** @brief Emits debug information for this buffer. */
    void debug(uint32_t idx);
};

/** @brief Shared pointer alias for `Buffer`. */
typedef std::shared_ptr<rogue::interfaces::stream::Buffer> BufferPtr;
}  // namespace stream
}  // namespace interfaces
}  // namespace rogue

#endif
