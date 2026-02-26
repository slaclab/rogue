/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    SLAC AXI Batcher V1
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
#ifndef __ROGUE_PROTOCOLS_BATCHER_CORE_V1_H__
#define __ROGUE_PROTOCOLS_BATCHER_CORE_V1_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <thread>
#include <vector>

#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Frame.h"

namespace rogue {
namespace protocols {
namespace batcher {

class Data;

/**
 * @brief Parser for SLAC AXI Batcher v1 super-frames.
 *
 * @details
 * Protocol reference: https://confluence.slac.stanford.edu/x/th1SDg
 *
 * `CoreV1` parses one incoming batched stream frame into:
 * - A super-header region.
 * - A list of per-record `Data` descriptors.
 * - A list of tail iterators for each record.
 *
 * This class is the shared parser used by `SplitterV1` and `InverterV1`.
 * - `SplitterV1` uses parsed `Data` records to emit one frame per batch entry.
 * - `InverterV1` uses parsed tail/header locations to rewrite framing in place.
 *
 * Record accessors (`record()`, `beginTail()`, `endTail()`) expose records in
 * stream order, even though parsing walks tails from the end of the frame.
 *
 * Threading model:
 * - No internal threads are created.
 * - The object is intended for single-threaded use per instance.
 */
class CoreV1 {
    std::shared_ptr<rogue::Logging> log_;

    // Most recently parsed frame.
    std::shared_ptr<rogue::interfaces::stream::Frame> frame_;

    // Parsed record descriptors.
    std::vector<std::shared_ptr<rogue::protocols::batcher::Data> > list_;

    // Parsed super-header size in bytes.
    uint32_t headerSize_;

    // Parsed per-record tail size in bytes.
    uint32_t tailSize_;

    // Iterators pointing to each parsed tail.
    std::vector<rogue::interfaces::stream::FrameIterator> tails_;

    // Parsed frame sequence number.
    uint32_t seq_;

  public:
    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Creates a `CoreV1` parser instance.
     *
     * @details
     * This static factory is the preferred construction path when the object
     * is shared across Rogue graph connections or exposed to Python.
     * It returns `std::shared_ptr` ownership compatible with Rogue pointer typedefs.
     *
     * @return Shared pointer to the created parser.
     */
    static std::shared_ptr<rogue::protocols::batcher::CoreV1> create();

    /**
     * @brief Constructs a `CoreV1` parser.
     *
     * @details
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` when shared ownership or Python exposure is required.
     */
    CoreV1();

    /** @brief Destroys the parser. */
    ~CoreV1();

    /**
     * @brief Pre-reserves internal record/tail container capacity.
     * @param size Expected maximum record count per frame.
     */
    void initSize(uint32_t size);

    /**
     * @brief Returns number of parsed records.
     * @return Parsed record count.
     */
    uint32_t count();

    /**
     * @brief Returns parsed super-header size.
     * @return Header size in bytes.
     */
    uint32_t headerSize();

    /**
     * @brief Returns iterator to beginning of parsed header.
     * @return Header-begin iterator.
     */
    rogue::interfaces::stream::FrameIterator beginHeader();

    /**
     * @brief Returns iterator to end of parsed header.
     * @return Header-end iterator.
     */
    rogue::interfaces::stream::FrameIterator endHeader();

    /**
     * @brief Returns parsed tail size per record.
     * @return Tail size in bytes.
     */
    uint32_t tailSize();

    /**
     * @brief Returns iterator to beginning of a parsed record tail.
     * @param index Zero-based record index in stream order.
     * @return Tail-begin iterator for requested record.
     */
    rogue::interfaces::stream::FrameIterator beginTail(uint32_t index);

    /**
     * @brief Returns iterator to end of a parsed record tail.
     * @param index Zero-based record index in stream order.
     * @return Tail-end iterator for requested record.
     */
    rogue::interfaces::stream::FrameIterator endTail(uint32_t index);

    /**
     * @brief Returns parsed data record descriptor by index.
     * @param index Zero-based record index in stream order.
     * @return Reference to parsed `Data` record pointer.
     */
    std::shared_ptr<rogue::protocols::batcher::Data>& record(uint32_t index);

    /**
     * @brief Returns parsed batch sequence number.
     * @return Sequence number from super-header.
     */
    uint32_t sequence();

    /**
     * @brief Parses a batched frame and populates parser state.
     *
     * @details
     * On success, header/tail metadata and record descriptors are available
     * through the accessor methods. On failure, parser state is reset and
     * `false` is returned.
     *
     * @param frame Input batched frame.
     * @return `true` if frame is valid and parsed; otherwise `false`.
     */
    bool processFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    /** @brief Clears parsed frame state and record lists. */
    void reset();
};

// Convienence
typedef std::shared_ptr<rogue::protocols::batcher::CoreV1> CoreV1Ptr;
}  // namespace batcher
}  // namespace protocols
}  // namespace rogue
#endif
