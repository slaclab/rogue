/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Stream frame iterator
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
#ifndef __ROGUE_INTERFACES_STREAM_FRAME_ACCESSOR_H__
#define __ROGUE_INTERFACES_STREAM_FRAME_ACCESSOR_H__
#include "rogue/Directives.h"

#include <inttypes.h>
#include <stdint.h>

#include <memory>

#include "rogue/GeneralError.h"
#include "rogue/interfaces/stream/FrameIterator.h"

namespace rogue {
namespace interfaces {
namespace stream {

/**
 * @brief Typed accessor over a contiguous frame-data region.
 */
template <typename T>
class FrameAccessor {
  private:
    // Data container
    T* data_;

    // Size value
    uint32_t size_;

  public:
    /**
     * @brief Creates a typed accessor at the iterator location.
     *
     * @param iter Frame iterator positioned at the first element.
     * @param size Number of elements in the accessor.
     * @throws rogue::GeneralError If the range spans multiple buffers.
     */
    FrameAccessor(rogue::interfaces::stream::FrameIterator& iter, uint32_t size) {
        data_ = reinterpret_cast<T*>(iter.ptr());
        size_ = size;

        if (size * sizeof(T) > iter.remBuffer())
            throw rogue::GeneralError::create("FrameAccessor",
                                              "Attempt to create a FrameAccessor over a multi-buffer range!");
    }

    /** 
     * @brief Dereference by index.
     * @details 
     * Returns element reference at `offset` (unchecked). 
     */
    T& operator[](const uint32_t offset) {
        return data_[offset];
    }

    /**
     * @brief Returns element reference at `offset` with bounds checking.
     *
     * @param offset Element index.
     * @return Element reference.
     * @throws rogue::GeneralError If `offset >= size()`.
     */
    T& at(const uint32_t offset) {
        if (offset >= size_)
            throw rogue::GeneralError::create("FrameAccessor",
                                              "Attempt to access element %" PRIu32 " with size %" PRIu32,
                                              offset,
                                              size_);

        return data_[offset];
    }

    /** @brief Returns number of elements in this accessor. */
    uint32_t size() {
        return size_;
    }

    /** @brief Returns pointer to first element. */
    T* begin() {
        return data_;
    }

    /** @brief Returns pointer one-past-last element. */
    T* end() {
        return data_ + size_;
    }
};
}  // namespace stream
}  // namespace interfaces
}  // namespace rogue

#endif
