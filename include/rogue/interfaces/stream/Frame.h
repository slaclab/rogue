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
#ifndef __ROGUE_INTERFACES_STREAM_FRAME_H__
#define __ROGUE_INTERFACES_STREAM_FRAME_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <mutex>
#include <thread>
#include <vector>

#include "rogue/EnableSharedFromThis.h"

#ifndef NO_PYTHON
    #include <boost/python.hpp>
#endif

namespace rogue {
namespace interfaces {
namespace stream {

class Buffer;
class FrameIterator;
class FrameLock;

/**
 * @brief Container for one stream frame payload and metadata.
 *
 * @details
 * In Rogue stream interfaces, each logical frame in flight is represented by one
 * `Frame` instance. The frame object does not directly allocate contiguous payload
 * memory. Instead, it owns an ordered list of `Buffer` objects that provide the
 * underlying storage.
 *
 * `FrameIterator` traverses payload bytes across buffer boundaries, so higher-level
 * protocol code can read or write frame content without manual buffer stitching.
 * The frame also carries transport metadata (`flags`, `channel`, `error`) and
 * payload accounting (`size`, `payload`, and available space).
 */
class Frame : public rogue::EnableSharedFromThis<rogue::interfaces::stream::Frame> {
    friend class Buffer;
    friend class FrameLock;

    // Interface specific flags
    uint16_t flags_;

    // Error state
    uint8_t error_;

    // Channel
    uint8_t chan_;

    // List of buffers which hold real data
    std::vector<std::shared_ptr<rogue::interfaces::stream::Buffer> > buffers_;

    // Total size of buffers
    uint32_t size_;

    // Total payload size
    uint32_t payload_;

    // Update buffer size counts
    void updateSizes();

    // Size values dirty flags
    bool sizeDirty_;

  protected:
    // Set size values dirty
    void setSizeDirty();

    // Frame lock
    std::mutex lock_;

  public:
    /** @brief Iterator alias for the internal buffer list. */
    typedef std::vector<std::shared_ptr<rogue::interfaces::stream::Buffer> >::iterator BufferIterator;

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Creates an empty frame.
     *
     * @details
     * Not exposed to Python.
     *
     * @return Shared pointer to the created frame.
     */
    static std::shared_ptr<rogue::interfaces::stream::Frame> create();

    /**
     * @brief Constructs an empty frame.
     *
     * @details
     * Usually created via `create()`.
     */
    Frame();

    /** @brief Destroys the frame instance. */
    ~Frame();

    /**
     * @brief Locks the frame and returns a scoped lock object.
     *
     * @details
     * Acquire this lock before operating on a `Frame` object from user code,
     * especially when reading or writing payload bytes, adjusting payload size,
     * or changing metadata fields (`flags`, `channel`, `error`). This is the
     * standard synchronization mechanism for frame access and should be treated
     * as required whenever a frame can be observed or modified outside a single
     * thread's private scope.
     *
     * Exposed as `lock()` in Python.
     *
     * @return Shared pointer to a `FrameLock`.
     */
    std::shared_ptr<rogue::interfaces::stream::FrameLock> lock();

    /**
     * @brief Appends another frame's buffers to the end of this frame.
     *
     * @details
     * Buffers from the passed frame are appended to the end of this frame and
     * will be removed from the source frame.
     *
     * Not exposed to Python.
     *
     * @param frame Source frame pointer (`FramePtr`) to append.
     * @return Iterator pointing to the first inserted buffer from `frame`.
     */
    std::vector<std::shared_ptr<rogue::interfaces::stream::Buffer> >::iterator appendFrame(
        std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    /**
     * @brief Appends one buffer to the end of the frame.
     *
     * @details
     * Not exposed to Python.
     *
     * This is for advanced manipulation of the underlying buffers.
     * @param buff Buffer pointer (`BufferPtr`) to append.
     * @return Iterator pointing to the added buffer.
     */
    std::vector<std::shared_ptr<rogue::interfaces::stream::Buffer> >::iterator appendBuffer(
        std::shared_ptr<rogue::interfaces::stream::Buffer> buff);

    /**
     * @brief Returns iterator to first underlying buffer.
     *
     * @details
     * Not exposed to Python.
     *
     * This is for advanced manipulation of the underlying buffers.
     * @return Iterator pointing to the start of the buffer list.
     */
    std::vector<std::shared_ptr<rogue::interfaces::stream::Buffer> >::iterator beginBuffer();

    /**
     * @brief Returns end iterator for underlying buffer list.
     *
     * @details
     * Not exposed to Python.
     *
     * This is for advanced manipulation of the underlying buffers.
     * @return Iterator pointing to the end of the buffer list.
     */
    std::vector<std::shared_ptr<rogue::interfaces::stream::Buffer> >::iterator endBuffer();

    /**
     * @brief Returns number of underlying buffers in the frame.
     *
     * @details
     * Not exposed to Python.
     *
     * This is for advanced manipulation of the underlying buffers.
     * @return Number of buffers in the list.
     */
    uint32_t bufferCount();

    /**
     * @brief Removes all buffers from the frame.
     *
     * @details
     * Not exposed to Python.
     */
    void clear();

    /**
     * @brief Returns whether the frame contains no buffers.
     *
     * @details
     * Not exposed to Python.
     *
     * @return `true` if frame buffer list is empty.
     */
    bool isEmpty();

    /**
     * @brief Returns total raw frame capacity in bytes.
     *
     * @details
     * This function returns the full buffer size.
     *
     * Exposed as `getSize()` in Python.
     *
     * @return Total raw buffer size of frame in bytes.
     */
    uint32_t getSize();

    /**
     * @brief Returns remaining available payload space in bytes.
     *
     * @details
     * This is the space remaining for payload.
     *
     * Exposed as `getAvailable()` in Python.
     *
     * @return Remaining bytes available for payload in the frame.
     */
    uint32_t getAvailable();

    /**
     * @brief Returns current payload size in bytes.
     *
     * Exposed as `getPayload()` in Python.
     *
     * @return Total payload bytes in the frame.
     */
    uint32_t getPayload();

    //! Set payload size
    /**
     * @brief Sets payload size in bytes.
     *
     * @details
     * Not exposed to Python.
     *
     * @param size New payload size
     */
    void setPayload(uint32_t size);

    //! Set payload size to at least the passed value
    /**
     * @brief Expands payload size to at least the passed value.
     *
     * @details
     * If current payload size is larger then passed value,
     * the payload size is unchanged.
     *
     * Not exposed to Python
     * @param size New minimum size
     */
    void minPayload(uint32_t size);

    //! Adjust payload size
    /**
     * @brief Adjusts payload size by a signed delta.
     *
     * @details
     * Pass is a positive or negative size adjustment.
     *
     * Not exposed to Python
     * @param value Size adjustment value
     */
    void adjustPayload(int32_t value);

    //! Set the Frame payload to full
    /**
     * @brief Sets payload size to full available frame capacity.
     *
     * @details
     * Set the current payload size to equal the total
     * available size of the buffers.
     *
     * Not exposed to Python
     */
    void setPayloadFull();

    /** @brief Sets the frame payload size to zero bytes. */
    void setPayloadEmpty();

    //! Get Frame flags
    /**
     * @brief Returns 16-bit frame flags field.
     *
     * @details
     * The Frame flags field is a 16-bit application specific field
     * for passing data between a stream Master and Slave.
     * A typical use in Rogue is to pass the first and last user
     * Axi-Stream fields.
     *
     * Exposed as getFlags() to Python
     * @return 16-bit Flag value
     */
    uint16_t getFlags();

    //! Set Frame flags
    /**
     * @brief Sets 16-bit frame flags field.
     *
     * Exposed as setFlags() to Python
     * @param flags 16-bit flag value
     */
    void setFlags(uint16_t flags);

    /**
     * @brief Returns the lower 8-bit user field from flags (SSI/Axi-Stream).
     *
     * @details
     * The first user value is stored in the lower 8 bits of the flag field.
     *
     * Exposed as getFirstuser() to Python
     * @return 8-bit first-user value.
     */
    uint8_t getFirstUser();

    /**
     * @brief Sets the lower 8-bit user field in flags (SSI/Axi-Stream).
     *
     * Exposed as `setFirstUser()` to Python.
     *
     * @param fuser 8-bit first-user value.
     */
    void setFirstUser(uint8_t fuser);

    /**
     * @brief Returns the upper 8-bit user field from flags (SSI/Axi-Stream).
     *
     * @details
     * The last user value is stored in the upper 8 bits of the flag field.
     *
     * Exposed as getLastUser() to Python
     * @return 8-bit last-user value.
     */
    uint8_t getLastUser();

    /**
     * @brief Sets the upper 8-bit user field in flags (SSI/Axi-Stream).
     *
     * Exposed as `setLastUser()` to Python.
     *
     * @param fuser 8-bit last-user value.
     */
    void setLastUser(uint8_t fuser);

    //! Get channel
    /**
     * @brief Returns frame channel value.
     *
     * @details
     * Most Frames in Rogue will not use this channel field since most
     * Master to Slave connections are not channelized. Exceptions include
     * data coming out of a data file reader.
     *
     * Exposed as getChannel() to Python
     * @return 8-bit channel ID
     */
    uint8_t getChannel();

    //! Set channel
    /**
     * @brief Sets frame channel value.
     *
     * Exposed as setChannel() to Python
     * @param channel 8-bit channel ID
     */
    void setChannel(uint8_t channel);

    //! Get error state
    /**
     * @brief Returns frame error status value.
     *
     * @details
     * The error value is application specific, depending on the stream Master
     * implementation. A non-zero value is considered an error.
     *
     * Exposed as getError() to Python
     * @return Error status value.
     */
    uint8_t getError();

    //! Set error state
    /**
     * @brief Sets frame error status value.
     *
     * Exposed as setError() to Python
     * @param error New error value
     */
    void setError(uint8_t error);

    //! Get begin FrameIterator
    /**
     * @brief Returns begin iterator over frame payload.
     *
     * @details
     * Return an iterator for accessing data within the Frame.
     * This iterator assumes the payload size of the frame has
     * already been set. This means the frame has either been
     * received already containing data, or the setPayload() method
     * has been called.
     *
     * Not exposed to Python
     * @return FrameIterator pointing to beginning of payload
     */
    rogue::interfaces::stream::FrameIterator begin();

    //! Get end FrameIterator
    /**
     * @brief Returns end iterator over frame payload.
     *
     * @details
     * This iterator is used to detect when the end of the
     * Frame payload is reached when iterating through the Frame.
     *
     * Not exposed to Python
     * @return FrameIterator read end position
     */
    rogue::interfaces::stream::FrameIterator end();

    /**
     * @brief Returns legacy read-begin iterator.
     *
     * @details
     * Legacy alias retained for compatibility. Prefer `begin()`.
     *
     * @return Iterator to payload start.
     */
    rogue::interfaces::stream::FrameIterator beginRead();

    /**
     * @brief Returns legacy read-end iterator.
     *
     * @details
     * Legacy alias retained for compatibility. Prefer `end()`.
     *
     * @return Iterator to payload end.
     */
    rogue::interfaces::stream::FrameIterator endRead();

    /**
     * @brief Returns legacy write-begin iterator.
     *
     * @details
     * Legacy alias retained for compatibility. Prefer `begin()`.
     *
     * @return Iterator to payload start.
     */
    rogue::interfaces::stream::FrameIterator beginWrite();

    /**
     * @brief Returns legacy write-end iterator.
     *
     * @details
     * Legacy alias retained for compatibility. Prefer `end()`.
     *
     * @return Iterator to payload end.
     */
    rogue::interfaces::stream::FrameIterator endWrite();

#ifndef NO_PYTHON

    //! Python Frame data read function.
    /** @brief Reads frame bytes into a passed Python bytearray/buffer.
     *
     * @details
     * Exposed as `read()` to Python.
     *
     * @param p Python object containing writable byte storage.
     * @param offset Byte offset in frame payload to start copying from.
     */
    void readPy(boost::python::object p, uint32_t offset);

    //! Python Frame data read function.
    /** @brief Reads frame bytes into a newly allocated Python bytearray.
     *
     * @details
     * Exposed as `getBa()` to Python.
     *
     * @param offset Byte offset in frame payload to start reading from.
     * @param count Number of bytes to read.
     * @return Python `bytearray` containing the copied bytes.
     */
    boost::python::object getBytearrayPy(uint32_t offset, uint32_t count);

    //! Python Frame data read function.
    /**
     * @brief Returns a Python `memoryview` of frame payload data.
     *
     * @details
     * Exposed as `getMemoryview()` to Python.
     *
     * @return Python memoryview object for frame payload.
     */
    boost::python::object getMemoryviewPy();

    //! Python Frame data write function.
    /** @brief Writes bytes from a Python bytearray/buffer into the frame.
     *
     * @details
     * Exposed as `write()` to Python.
     *
     * @param p Python object containing source byte storage.
     * @param offset Byte offset in frame payload to start writing to.
     */
    void writePy(boost::python::object p, uint32_t offset);

    /**
     * @brief Reads frame data and returns it as a NumPy `uint8` array.
     *
     * @param offset Byte offset in frame payload to start reading from.
     * @param count Number of bytes to read.
     * @return One-dimensional NumPy array of `uint8`.
     */
    boost::python::object getNumpy(uint32_t offset, uint32_t count);

    /**
     * @brief Writes NumPy array data into the frame payload.
     *
     * @param np NumPy array containing source bytes.
     * @param offset Byte offset in frame payload to start writing to.
     */
    void putNumpy(boost::python::object np, uint32_t offset);
#endif

    /** @brief Prints debug information for this frame. */
    void debug();
};

/** @brief Shared pointer alias for `Frame`. */
typedef std::shared_ptr<rogue::interfaces::stream::Frame> FramePtr;
}  // namespace stream
}  // namespace interfaces
}  // namespace rogue

#endif
