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
#ifndef __ROGUE_INTERFACES_STREAM_FRAME_ITERATOR_H__
#define __ROGUE_INTERFACES_STREAM_FRAME_ITERATOR_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <cstring>
#include <memory>
#include <vector>

namespace rogue {
namespace interfaces {
namespace stream {

class Frame;
class Buffer;

/**
 * @brief Random-access byte iterator across a `Frame` payload.
 *
 * @details
 * `FrameIterator` provides STL-style random-access semantics over frame payload
 * bytes, even when payload storage spans multiple underlying buffers. It hides
 * buffer boundary transitions and allows efficient copy operations with helper
 * APIs (`toFrame`, `fromFrame`, `copyFrame`).
 *
 * This class is C++ only and is not exposed directly to Python.
 */
class FrameIterator : public std::iterator<std::random_access_iterator_tag, uint8_t> {
    friend class Frame;

  private:
    // Creator
    FrameIterator(std::shared_ptr<rogue::interfaces::stream::Frame> frame, bool write, bool end);

    // write flag
    bool write_;

    // Associated frame
    std::shared_ptr<rogue::interfaces::stream::Frame> frame_;

    // Frame position
    int32_t framePos_;

    // Frame size
    int32_t frameSize_;

    // current buffer
    std::vector<std::shared_ptr<rogue::interfaces::stream::Buffer> >::iterator buff_;

    // Buffer position
    int32_t buffBeg_;

    // Buffer size
    int32_t buffEnd_;

    // Current buffer iterator
    uint8_t* data_;

    // increment position
    inline void increment(int32_t diff);

    // decrement position
    inline void decrement(int32_t diff);

  public:
    /** @brief Constructs an empty iterator for later assignment. */
    FrameIterator();

    /**
     * @brief Copy-assigns iterator state.
     *
     * @param rhs Source iterator.
     * @return Copy of the assigned iterator.
     */
    const rogue::interfaces::stream::FrameIterator operator=(const rogue::interfaces::stream::FrameIterator& rhs);

    /**
     * @brief Returns iterator marking the end of the current buffer segment.
     *
     * @details
     * The returned iterator is an end marker for the current buffer, and
     * possibly the end of the frame. If the current Buffer is followed by
     * another buffer containing valid data for a Read or available space for a write,
     * the returned iterator will mark the start of the next Buffer. Having this
     * iterator is useful when iterating through contiguous memory blocks for more
     * efficient data copying when using std::copy().
     *
     * @return Iterator marking the end of the current buffer span.
     */
    rogue::interfaces::stream::FrameIterator endBuffer();

    /**
     * @brief Returns remaining bytes in the current buffer span.
     *
     * @details
     * Similar to `endBuffer()`, this returns remaining bytes in the current
     * underlying buffer region without crossing to the next one.
     *
     * @return Remaining bytes in the current buffer.
     */
    uint32_t remBuffer();

    /**
     * @brief Dereferences iterator to current byte.
     *
     * @details
     * Allows data at the current iterator position to be accessed using
     * `*it` syntax.
     *
     * @return Reference to current byte.
     */
    uint8_t& operator*() const;

    // uint8_t * operator ->() const;

    /**
     * @brief Returns pointer to byte at current iterator position.
     * @return Pointer to current byte location.
     */
    uint8_t* ptr() const;

    /**
     * @brief Returns byte value at relative offset from current position.
     *
     * @param offset Relative offset to access.
     * @return Data byte at passed offset.
     */
    uint8_t operator[](const uint32_t offset) const;

    /**
     * @brief Prefix-increments iterator by one byte.
     *
     * @details
     * Increment the current iterator position by a single location
     * and return a reference to the current iterator.
     *
     * @return Reference to iterator at the new position.
     */
    const rogue::interfaces::stream::FrameIterator& operator++();

    /**
     * @brief Postfix-increments iterator by one byte.
     *
     * @details
     * Increment the current iterator position by a single location
     * and return a reference to the previous iterator position. This
     * results in a copy of the iterator being created before the increment.
     *
     * @return Reference to iterator at the old position.
     */
    rogue::interfaces::stream::FrameIterator operator++(int);

    /**
     * @brief Prefix-decrements iterator by one byte.
     *
     * @details
     * Decrement the current iterator position by a single location
     * and return a reference to the current iterator.
     *
     * @return Reference to iterator at the new position.
     */
    const rogue::interfaces::stream::FrameIterator& operator--();

    /**
     * @brief Postfix-decrements iterator by one byte.
     *
     * @details
     * Decrement the current iterator position by a single location
     * and return a reference to the previous iterator position. This
     * results in a copy of the iterator being created before the decrement.
     *
     * @return Reference to iterator at the old position.
     */
    rogue::interfaces::stream::FrameIterator operator--(int);

    /**
     * @brief Compares two iterators for inequality.
     *
     * @details
     * Compare this iterator to another iterator and return `true` if they are at
     * different positions.
     *
     * @param other Iterator to compare against.
     * @return `true` if the two iterators are not equal.
     */
    bool operator!=(const rogue::interfaces::stream::FrameIterator& other) const;

    /**
     * @brief Compares two iterators for equality.
     *
     * @details
     * Compare this iterator to another iterator and return `true` if they
     * reference the same position within the frame.
     *
     * @param other Iterator to compare against.
     * @return `true` if the two iterators are equal.
     */
    bool operator==(const rogue::interfaces::stream::FrameIterator& other) const;

    /**
     * @brief Returns whether this iterator is before another iterator.
     *
     * @details
     * Compare this iterator to another iterator and return `true` if the local
     * iterator (left of `<`) is less than the iterator being compared against.
     *
     * @param other Iterator to compare against.
     * @return `true` if the left iterator is less than the right.
     */
    bool operator<(const rogue::interfaces::stream::FrameIterator& other) const;

    /**
     * @brief Returns whether this iterator is after another iterator.
     *
     * @details
     * Compare this iterator to another iterator and return `true` if the local
     * iterator (left of `>`) is greater than the iterator being compared against.
     *
     * @param other Iterator to compare against.
     * @return `true` if the left iterator is greater than the right.
     */
    bool operator>(const rogue::interfaces::stream::FrameIterator& other) const;

    /**
     * @brief Returns whether this iterator is before or equal to another iterator.
     *
     * @details
     * Compare this iterator to another iterator and return `true` if the local
     * iterator (left of `<=`) is less than or equal to the iterator being compared against.
     *
     * @param other Iterator to compare against.
     * @return `true` if the left iterator is less than or equal to the right.
     */
    bool operator<=(const rogue::interfaces::stream::FrameIterator& other) const;

    /**
     * @brief Returns whether this iterator is after or equal to another iterator.
     *
     * @details
     * Compare this iterator to another iterator and return `true` if the local
     * iterator (left of `>=`) is greater than or equal to the iterator being compared against.
     *
     * @param other Iterator to compare against.
     * @return `true` if the left iterator is greater than or equal to the right.
     */
    bool operator>=(const rogue::interfaces::stream::FrameIterator& other) const;

    /**
     * @brief Returns a new iterator offset forward by `add`.
     *
     * @details
     * Create a new iterator and increment its position by the passed value.
     *
     * @param add Positive or negative value to increment the current position by.
     * @return New iterator at the new position.
     */
    rogue::interfaces::stream::FrameIterator operator+(const int32_t add) const;

    /**
     * @brief Returns a new iterator offset backward by `sub`.
     *
     * @details
     * Create a new iterator and decrement its position by the passed value.
     *
     * @param sub Positive or negative value to decrement the current position by.
     * @return New iterator at the new position.
     */
    rogue::interfaces::stream::FrameIterator operator-(const int32_t sub) const;

    /**
     * @brief Returns byte-distance between two iterators.
     *
     * @details
     * Return the difference between the current iterator position (left of `-`)
     * and the compared iterator position.
     *
     * @param other Iterator to compare against.
     * @return Difference of the two positions as an `int32_t`.
     */
    int32_t operator-(const rogue::interfaces::stream::FrameIterator& other) const;

    /**
     * @brief In-place increments iterator by `add`.
     *
     * @details
     * Increment the current iterator by the passed value.
     *
     * @param add Positive or negative value to increment the current position by.
     * @return Reference to current iterator at the new position.
     */
    rogue::interfaces::stream::FrameIterator& operator+=(const int32_t add);

    /**
     * @brief In-place decrements iterator by `sub`.
     *
     * @details
     * Decrement the current iterator by the passed value.
     *
     * @param sub Positive or negative value to decrement the current position by.
     * @return Reference to current iterator at the new position.
     */
    rogue::interfaces::stream::FrameIterator& operator-=(const int32_t sub);
};

/**
 * @brief Copies bytes from a source pointer into a frame iterator.
 *
 * @details
 * This helper function copies from the passed data pointer into the
 * Frame at the iterator position. The iterator is incremented by the copy size.
 *
 * @param iter FrameIterator at position to copy the data to.
 * @param size Number of bytes to copy.
 * @param src Pointer to source data.
 */
static inline void toFrame(rogue::interfaces::stream::FrameIterator& iter, uint32_t size, void* src) {
    uint8_t* ptr = reinterpret_cast<uint8_t*>(src);
    uint32_t csize;

    do {
        csize = (size > iter.remBuffer()) ? iter.remBuffer() : size;
        std::memcpy(iter.ptr(), ptr, csize);
        ptr += csize;
        iter += csize;
        size -= csize;
    } while (size > 0 && csize > 0);
}

/**
 * @brief Copies bytes from a frame iterator to a destination pointer.
 *
 * @details
 * This helper function copies data from the frame at the iterator location
 * into the passed data pointer. The iterator is updated by byte copy size.
 *
 * @param iter FrameIterator at position to copy the data from.
 * @param size Number of bytes to copy.
 * @param dst Pointer to destination data.
 */
static inline void fromFrame(rogue::interfaces::stream::FrameIterator& iter, uint32_t size, void* dst) {
    uint8_t* ptr = reinterpret_cast<uint8_t*>(dst);
    uint32_t csize;

    do {
        csize = (size > iter.remBuffer()) ? iter.remBuffer() : size;
        std::memcpy(ptr, iter.ptr(), csize);
        ptr += csize;
        iter += csize;
        size -= csize;
    } while (size > 0 && csize > 0);
}

/**
 * @brief Copies bytes between frame iterators.
 *
 * @details
 * This helper function copies data from the source frame at the iterator
 * location into the dest frame at the iterator location. Both iterators are
 * updated by byte copy size.
 *
 * @param srcIter FrameIterator at position to copy the data from.
 * @param size Number of bytes to copy.
 * @param dstIter FrameIterator at position to copy the data to.
 */
static inline void copyFrame(rogue::interfaces::stream::FrameIterator& srcIter,
                             uint32_t size,
                             rogue::interfaces::stream::FrameIterator& dstIter) {
    uint32_t csize;

    do {
        csize = (size > srcIter.remBuffer()) ? srcIter.remBuffer() : size;
        csize = (csize > dstIter.remBuffer()) ? dstIter.remBuffer() : csize;
        std::memcpy(dstIter.ptr(), srcIter.ptr(), csize);
        srcIter += csize;
        dstIter += csize;
        size -= csize;
    } while (size > 0 && csize > 0);
}
}  // namespace stream
}  // namespace interfaces
}  // namespace rogue

#endif
