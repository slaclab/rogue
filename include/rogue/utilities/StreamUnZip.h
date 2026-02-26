/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    Stream modules to decompress a data stream
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
#ifndef __ROGUE_UTILITIES_STREAM_UN_ZIP_H__
#define __ROGUE_UTILITIES_STREAM_UN_ZIP_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <thread>

#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"

namespace rogue {
namespace utilities {

/**
 * @brief Stream module that decompresses bzip2-compressed frame payloads.
 *
 * @details
 * `StreamUnZip` consumes compressed frames on its slave side, inflates the
 * payload bytes, and forwards a new frame downstream from its master side.
 * Frame metadata (channel, flags, error state) is preserved.
 *
 * Output frame allocation is requested via `reqFrame()`. The implementation
 * starts with an output frame sized to the compressed payload and grows it if
 * the decompressed data requires additional space.
 *
 * Threading model:
 * - `StreamUnZip` does not create an internal worker thread.
 * - Decompression runs synchronously in the caller thread that invokes
 *   `acceptFrame()`.
 * - A lock is taken on the input frame while payload buffers are read, so the
 *   compressed frame contents are stable during decompression.
 */
class StreamUnZip : public rogue::interfaces::stream::Slave, public rogue::interfaces::stream::Master {
  public:
    /**
     * @brief Creates a stream decompressor instance.
     *
     * @details
     * This static factory is the preferred construction path when the object
     * is shared across Rogue graph connections or exposed to Python.
     * It returns `std::shared_ptr` ownership compatible with Rogue pointer typedefs.
     *
     * @return Shared pointer to the created decompressor.
     */
    static std::shared_ptr<rogue::utilities::StreamUnZip> create();

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Constructs a stream decompressor.
     *
     * @details
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` when shared ownership or Python exposure is required.
     */
    StreamUnZip();

    /** @brief Destroys stream decompressor. */
    ~StreamUnZip();

    /**
     * @brief Accepts a compressed frame, decompresses payload, and forwards it.
     * @param frame Input compressed frame.
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

// Convenience
typedef std::shared_ptr<rogue::utilities::StreamUnZip> StreamUnZipPtr;
}  // namespace utilities
}  // namespace rogue
#endif
