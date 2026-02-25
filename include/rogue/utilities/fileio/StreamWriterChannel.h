/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    Class to act as a slave interface to the StreamWriter. Each
 *    slave is associated with a tag. The tag is included in the bank header
 *    of each write.
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
#ifndef __ROGUE_UTILITIES_FILEIO_STREAM_WRITER_CHANNEL_H__
#define __ROGUE_UTILITIES_FILEIO_STREAM_WRITER_CHANNEL_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <thread>

#include "rogue/interfaces/stream/Slave.h"

namespace rogue {
namespace utilities {
namespace fileio {

class StreamWriter;

/**
 * @brief Stream sink that writes incoming frames into a tagged writer channel.
 *
 * @details
 * `StreamWriterChannel` is a `stream::Slave` front end for `StreamWriter`.
 * Each instance is bound to a channel/tag value used in the output file bank
 * header. If constructed with `channel == 0`, the channel is taken from each
 * incoming frame (`frame->getChannel()`); otherwise the configured channel is
 * forced for all writes.
 *
 * The class also tracks how many frames have been accepted so callers can
 * synchronize on data capture progress with `waitFrameCount()`.
 */
class StreamWriterChannel : public rogue::interfaces::stream::Slave {
    // Associated stream writer instance.
    std::shared_ptr<rogue::utilities::fileio::StreamWriter> writer_;

    // Fixed output channel, or 0 to use incoming frame channel.
    uint8_t channel_;

    // Number of frames accepted by this channel.
    uint32_t frameCount_;

    // Lock protecting frame counter and wait condition.
    std::mutex mtx_;

    // Condition signaled when frameCount_ changes.
    std::condition_variable cond_;

  public:
    /**
     * @brief Creates a stream writer channel instance.
     * @param writer Destination writer used to serialize frames.
     * @param channel Output channel/tag. Use `0` to forward per-frame channel.
     * @return Shared pointer to the created channel.
     */
    static std::shared_ptr<rogue::utilities::fileio::StreamWriterChannel> create(
        std::shared_ptr<rogue::utilities::fileio::StreamWriter> writer,
        uint8_t channel);

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Constructs a stream writer channel.
     * @param writer Destination writer used to serialize frames.
     * @param channel Output channel/tag. Use `0` to forward per-frame channel.
     */
    StreamWriterChannel(std::shared_ptr<rogue::utilities::fileio::StreamWriter> writer, uint8_t channel);

    /** @brief Destroys stream writer channel. */
    ~StreamWriterChannel();

    /**
     * @brief Accepts and writes one incoming frame.
     *
     * @details
     * The method writes the frame through `StreamWriter`, increments the local
     * accepted-frame counter, and wakes waiters in `waitFrameCount()`.
     *
     * @param frame Input frame to write.
     */
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    /**
     * @brief Returns the number of accepted frames.
     * @return Accepted frame count.
     */
    uint32_t getFrameCount();

    /**
     * @brief Sets the accepted-frame counter to a specific value.
     * @param count New frame counter value.
     */
    void setFrameCount(uint32_t count);

    /**
     * @brief Waits until at least `count` frames have been accepted.
     *
     * @param count Target accepted-frame count.
     * @param timeout Timeout in microseconds. `0` waits indefinitely.
     * @return `true` if `count` was reached before timeout, else `false`.
     */
    bool waitFrameCount(uint32_t count, uint64_t timeout);
};

// Convenience
typedef std::shared_ptr<rogue::utilities::fileio::StreamWriterChannel> StreamWriterChannelPtr;
}  // namespace fileio
}  // namespace utilities
}  // namespace rogue

#endif
