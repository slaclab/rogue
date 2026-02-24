/**
  * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    Class to coordinate data file writing.
 *    This class supports multiple stream slaves, each with the ability to
 *    write to a common data file. The data file is a series of banks.
 *    Each bank has a channel and frame flags. The channel is per source and the
 *    lower 24 bits of the frame flags are used as the flags.
 *    The bank is proceeded by 2 - 32-bit headers to indicate bank information
 *    and length:
 *
 *       headerA:
 *          [31:0] = Length of data block in bytes
 *       headerB
 *          31:24  = Channel ID
 *          23:16  = Frame error
 *          15:0   = Frame flags
 *
 *    Optionally a flag can be set which writes the raw frame data directly to the file.
 *
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
#ifndef __ROGUE_UTILITIES_FILEIO_STREAM_WRITER_H__
#define __ROGUE_UTILITIES_FILEIO_STREAM_WRITER_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <chrono>
#include <condition_variable>
#include <deque>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <utility>

#include "rogue/EnableSharedFromThis.h"
#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Frame.h"

namespace rogue {
namespace utilities {
namespace fileio {

class StreamWriterChannel;

/**
 * @brief Stream writer coordination class.
 *
 * @details
 * Coordinates channelized frame capture into a single file stream with
 * optional banked framing metadata.
 */
class StreamWriter : public rogue::EnableSharedFromThis<rogue::utilities::fileio::StreamWriter> {
    friend class StreamWriterChannel;

  protected:
    // Log
    std::shared_ptr<rogue::Logging> log_;

    //! File descriptor
    int32_t fd_;

    //! Base file name
    std::string baseName_;

    //! Current file index
    bool isOpen_;

    //! Current file index
    uint32_t fdIdx_;

    //! Size limit for auto close and re-open when limit is exceeded, zero to disable
    uint64_t sizeLimit_;

    //! Current file size in bytes
    uint64_t currSize_;

    //! Total file size in bytes
    uint64_t totSize_;

    //! Buffering size to cache file writes, zero if disabled
    uint32_t buffSize_;

    //! Write buffer
    uint8_t* buffer_;

    //! Write buffer count
    uint32_t currBuffer_;

    //! Drop errors flag
    bool dropErrors_;

    //! File access lock
    std::mutex mtx_;

    //! Total number of frames in file
    uint32_t frameCount_;

    //! Bytes recorded in the last one second window
    uint64_t bandwidthBytes_;

    //! Time tagged byte counts for bandwidth calculation
    std::deque<std::pair<std::chrono::steady_clock::time_point, uint32_t>> bandwidthHistory_;

    //! Internal method for file writing
    void intWrite(void* data, uint32_t size);

    //! Check file size for next write
    void checkSize(uint32_t size);

    //! Flush file
    void flush();

    //! Update bandwidth accounting
    void recordBandwidth(uint32_t size);

    //! Remove stale bandwidth samples
    void pruneBandwidth(std::chrono::steady_clock::time_point now);

    //! Write raw data
    bool raw_;

    //! condition
    std::condition_variable cond_;

    std::map<uint32_t, std::shared_ptr<rogue::utilities::fileio::StreamWriterChannel>> channelMap_;

    //! Write data to file. Called from StreamWriterChannel
    virtual void writeFile(uint8_t channel, std::shared_ptr<rogue::interfaces::stream::Frame> frame);

  public:
    /**
     * @brief Creates a stream writer instance.
     * @return Shared pointer to the created writer.
     */
    static std::shared_ptr<rogue::utilities::fileio::StreamWriter> create();

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /** @brief Constructs a stream writer. */
    StreamWriter();

    /** @brief Destroys the stream writer and closes open resources. */
    virtual ~StreamWriter();

    /**
     * @brief Opens a data file.
     * @param file Output file path.
     */
    void open(std::string file);

    /** @brief Closes the currently open data file. */
    void close();

    /**
     * @brief Returns whether a data file is open.
     * @return True if a file is open.
     */
    bool isOpen();

    /**
     * @brief Sets raw output mode.
     * @param raw True to write raw frame payload only.
     */
    void setRaw(bool raw);

    /**
     * @brief Gets raw output mode state.
     * @return True when raw output mode is enabled.
     */
    bool getRaw();

    /**
     * @brief Sets write buffering size.
     * @param size Buffer size in bytes, 0 disables buffering.
     */
    void setBufferSize(uint32_t size);

    /**
     * @brief Sets automatic file rollover size.
     * @param size Maximum file size in bytes, 0 for unlimited.
     */
    void setMaxSize(uint64_t size);

    /**
     * @brief Configures whether errored frames are dropped.
     * @param drop True to drop errored frames instead of writing them.
     */
    void setDropErrors(bool drop);

    /**
     * @brief Gets or creates a channel writer endpoint.
     * @param channel Channel ID.
     * @return Channel writer object bound to \p channel.
     */
    std::shared_ptr<rogue::utilities::fileio::StreamWriterChannel> getChannel(uint8_t channel);

    /**
     * @brief Returns cumulative bytes written across all files.
     * @return Total written bytes.
     */
    uint64_t getTotalSize();

    /**
     * @brief Returns current output file size.
     * @return Current file size in bytes.
     */
    uint64_t getCurrentSize();

    /**
     * @brief Returns recent write bandwidth estimate.
     * @return Bandwidth in bytes per second.
     */
    double getBandwidth();

    /**
     * @brief Returns number of frames written to the current file session.
     * @return Frame count.
     */
    uint32_t getFrameCount();

    /**
     * @brief Blocks until a target frame count is reached or timeout expires.
     * @param count Target frame count threshold.
     * @param timeout Timeout in microseconds.
     * @return True if threshold reached before timeout.
     */
    bool waitFrameCount(uint32_t count, uint64_t timeout);
};

// Convenience
typedef std::shared_ptr<rogue::utilities::fileio::StreamWriter> StreamWriterPtr;
}  // namespace fileio
}  // namespace utilities
}  // namespace rogue
#endif
