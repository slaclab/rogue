/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    Stream modules to compress a data stream
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
#ifndef __ROGUE_UTILITIES_STREAM_ZIP_H__
#define __ROGUE_UTILITIES_STREAM_ZIP_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <thread>

#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"
namespace rogue {
namespace utilities {

/**
 * @brief Stream module that compresses frame payloads using bzip2.
 *
 * @details
 * `StreamZip` consumes frames on its slave side, compresses the payload bytes,
 * and forwards a new frame downstream from its master side. Frame metadata
 * (channel, flags, error state) is preserved.
 *
 * Output frame allocation is requested via `reqFrame()`. The implementation
 * starts with an output frame sized to the input payload and grows it if needed.
 *
 * Threading model:
 * - `StreamZip` does not create an internal worker thread.
 * - Compression runs synchronously in the caller thread that invokes
 *   `acceptFrame()`.
 * - A lock is taken on the input frame while payload buffers are read, so the
 *   frame contents are stable during compression.
 */
class StreamZip : public rogue::interfaces::stream::Slave, public rogue::interfaces::stream::Master {
  public:
    /**
     * @brief Creates a stream compressor instance.
     * @return Shared pointer to the created compressor.
     */
    static std::shared_ptr<rogue::utilities::StreamZip> create();

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /** @brief Constructs a stream compressor. */
    StreamZip();

    /** @brief Destroys stream compressor. */
    ~StreamZip();

    /**
     * @brief Accepts a frame, compresses its payload, and forwards the result.
     * @param frame Input frame to compress.
     */
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    /**
     * @brief Forwards frame-allocation requests upstream.
     * @param size Requested payload size in bytes.
     * @param zeroCopyEn `true` to request zero-copy buffer handling.
     * @return Allocated frame from upstream master path.
     */
    std::shared_ptr<rogue::interfaces::stream::Frame> acceptReq(uint32_t size, bool zeroCopyEn);
};

// Convienence
typedef std::shared_ptr<rogue::utilities::StreamZip> StreamZipPtr;
}  // namespace utilities
}  // namespace rogue
#endif
