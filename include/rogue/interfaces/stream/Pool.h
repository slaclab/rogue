/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Stream memory pool
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
#ifndef __ROGUE_INTERFACES_STREAM_POOL_H__
#define __ROGUE_INTERFACES_STREAM_POOL_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <queue>
#include <thread>

#include "rogue/EnableSharedFromThis.h"
#include "rogue/Queue.h"

namespace rogue {
namespace interfaces {
namespace stream {

class Frame;
class Buffer;

/**
 * @brief Frame and buffer allocator for stream endpoints.
 *
 * @details
 * `Pool` is the stream-memory allocation layer used by `Slave` objects to
 * service frame requests from upstream `Master` objects (`Master::reqFrame()`
 * eventually resolves through `Pool::acceptReq()` on the primary slave).
 *
 * Core responsibilities:
 * - Allocate and construct `Frame` objects.
 * - Allocate and construct the underlying `Buffer` objects used by each frame.
 * - Reclaim and optionally recycle buffer data when buffers are returned.
 * - Track allocation statistics (`getAllocBytes()`, `getAllocCount()`).
 *
 * Default behavior:
 * - A request typically returns a frame with one buffer sized for the request.
 * - Buffer memory is released when returned (no caching required).
 *
 * Fixed-size mode (`setFixedSize()`):
 * - Each allocated buffer uses the configured fixed buffer size.
 * - If a frame request is larger than one fixed buffer, the frame is built from
 *   multiple buffers so total capacity satisfies the request.
 *
 * Pooling mode (`setPoolSize()` with fixed-size operation):
 * - Returned buffer memory blocks are cached in an internal free queue for reuse.
 * - Pool size defines the maximum number of cached entries retained.
 * - Reuse reduces allocator churn for high-rate streaming workloads.
 *
 * Subclassing/advanced use:
 * - Override `acceptReq()` to customize how frames are assembled.
 * - Override `retBuffer()` to customize return/recycle behavior.
 * - Use protected helpers (`allocBuffer()`, `createBuffer()`, `decCounter()`)
 *   when integrating external memory providers, such as DMA-backed memory.
 */
class Pool : public rogue::EnableSharedFromThis<rogue::interfaces::stream::Pool> {
    // Mutex
    std::mutex mtx_;

    // Track buffer allocations
    uint32_t allocMeta_;

    // Total memory allocated
    uint32_t allocBytes_;

    // Total buffers allocated
    uint32_t allocCount_;

    // Buffer queue
    std::queue<uint8_t*> dataQ_;

    // Fixed size buffer mode
    uint32_t fixedSize_;

    // Buffer queue count
    uint32_t poolSize_;

  public:
    /** @brief Constructs a pool with default allocation behavior enabled. */
    Pool();

    /** @brief Destroys the pool and releases any cached buffer storage. */
    virtual ~Pool();

    /**
     * @brief Returns total currently allocated bytes.
     *
     * @details
     * This value is incremented
     * as buffers are allocated and decremented as buffers are freed.
     *
     * Exposed as `getAllocBytes()` in Python.
     *
     * @return Total currently allocated bytes.
     */
    uint32_t getAllocBytes();

    /**
     * @brief Returns total currently allocated buffer count.
     *
     * @details
     * This value is incremented
     * as buffers are allocated and decremented as buffers are freed.
     *
     * Exposed as `getAllocCount()` in Python.
     *
     * @return Total currently allocated buffers.
     */
    uint32_t getAllocCount();

    /**
     * @brief Services a frame allocation request from a master.
     *
     * @details
     * Called by Master::reqFrame() to allocate a frame and one or more buffers.
     *
     * @param size Minimum requested payload size in bytes.
     * @param zeroCopyEn True to allow zero-copy buffers when supported.
     * @return Newly allocated frame.
     */
    virtual std::shared_ptr<rogue::interfaces::stream::Frame> acceptReq(uint32_t size, bool zeroCopyEn);

    /**
     * @brief Returns buffer data to the allocator.
     *
     * @details
     * This method is called by the Buffer destructor in order to free
     * the associated Buffer memory. May be overridden by a subclass to
     * change the way the buffer data is returned.
     *
     * @param data Data pointer to release.
     * @param meta Metadata specific to the allocator.
     * @param size Size of data buffer.
     */
    virtual void retBuffer(uint8_t* data, uint32_t meta, uint32_t size);

    /** @brief Registers this type with Python bindings. */
    static void setup_python();

    /**
     * @brief Sets fixed-size mode.
     *
     * @details
     * This method puts the allocator into fixed size mode.
     *
     * Exposed as `setFixedSize()` in Python.
     *
     * @param size Fixed size value.
     */
    void setFixedSize(uint32_t size);

    /**
     * @brief Returns fixed-size allocation setting.
     *
     * @details
     * A return value of `0` means fixed-size mode is disabled.
     *
     * Exposed as `getFixedSize()` in Python.
     *
     * @return Fixed size value or `0` when fixed-size mode is disabled.
     */
    uint32_t getFixedSize();

    /**
     * @brief Sets buffer pool size.
     *
     * Exposed as `setPoolSize()` in Python.
     *
     * @param size Number of entries to keep in the pool.
     */
    void setPoolSize(uint32_t size);

    /**
     * @brief Returns configured maximum number of cached pool entries.
     *
     * Exposed as `getPoolSize()` in Python.
     *
     * @return Pool size.
     */
    uint32_t getPoolSize();

  protected:
    /**
     * Allocate and Create a Buffer
     * This method is the default Buffer allocator. The requested
     * buffer is created from either a malloc call or fulling a free entry from
     * the memory pool if it is enabled. If fixed size is configured the
     * size parameter is ignored and a Buffer is returned with the fixed size
     * amount of memory. The passed total value is incremented by the
     * allocated Buffer size. This method is protected to allow it to be called
     * by a sub-class of Pool.
     *
     * Not exposed to Python
     * @param size Buffer size requested
     * @param total Pointer to current total size
     * @return Allocated Buffer pointer as BufferPtr
     */
    std::shared_ptr<rogue::interfaces::stream::Buffer> allocBuffer(uint32_t size, uint32_t* total);

    /**
     * @brief Creates a Buffer with a pre-allocated data block.
     *
     * @details
     * This method is used to create a Buffer with a pre-allocated block of
     * memory. This can be used when the block of memory is allocated by a
     * hardware DMA driver. This method is protected to allow it to be called
     * by a sub-class of Pool.
     *
     * Not exposed to Python
     * @param data Data pointer to pre-allocated memory block
     * @param meta Meta data associated with pre-allocated memory block
     * @param size Usable size of memory block (may be smaller than allocated size)
     * @param alloc Allocated size of memory block (may be greater than requested size)
     * @return Allocated Buffer pointer as BufferPtr
     */
    std::shared_ptr<rogue::interfaces::stream::Buffer> createBuffer(void* data,
                                                                    uint32_t meta,
                                                                    uint32_t size,
                                                                    uint32_t alloc);

    /**
     * @brief Decrements allocation counter.
     *
     * @details
     * Called in a sub-class to decrement the allocated byte count
     *
     * Not exposed to Python
     * @param alloc Amount of memory be de-allocated.
     */
    void decCounter(uint32_t alloc);
};

/** @brief Shared pointer alias for `Pool`. */
typedef std::shared_ptr<rogue::interfaces::stream::Pool> PoolPtr;
}  // namespace stream
}  // namespace interfaces
}  // namespace rogue
#endif
