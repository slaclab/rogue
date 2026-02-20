/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    SLAC AXI Batcher V2
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
#ifndef __ROGUE_PROTOCOLS_BATCHER_CORE_V2_H__
#define __ROGUE_PROTOCOLS_BATCHER_CORE_V2_H__
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

//!  AXI Stream FIFO
class CoreV2 {
    std::shared_ptr<rogue::Logging> log_;

    //! Frame pointers
    std::shared_ptr<rogue::interfaces::stream::Frame> frame_;

    //! Data List
    std::vector<std::shared_ptr<rogue::protocols::batcher::Data> > list_;

    //! Header size
    uint32_t headerSize_;

    //! Tail size
    uint32_t tailSize_;

    //! Tail pointers
    std::vector<rogue::interfaces::stream::FrameIterator> tails_;

    //! Sequence number
    uint32_t seq_;

  public:
    //! Setup class in python
    static void setup_python();

    //! Create class
    static std::shared_ptr<rogue::protocols::batcher::CoreV2> create();

    //! Creator
    CoreV2();

    //! Deconstructor
    ~CoreV2();

    //! Init size for internal containers
    void initSize(uint32_t size);

    //! Record count
    uint32_t count();

    //! Get header size
    uint32_t headerSize();

    //! Get beginning of header iterator
    rogue::interfaces::stream::FrameIterator beginHeader();

    //! Get end of header iterator
    rogue::interfaces::stream::FrameIterator endHeader();

    //! Get tail size
    uint32_t tailSize();

    //! Get beginning of tail iterator
    rogue::interfaces::stream::FrameIterator beginTail(uint32_t index);

    //! Get end of tail iterator
    rogue::interfaces::stream::FrameIterator endTail(uint32_t index);

    //! Get data
    std::shared_ptr<rogue::protocols::batcher::Data>& record(uint32_t index);

    //! Return sequence
    uint32_t sequence();

    //! Process a frame
    bool processFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    //! Reset data
    void reset();
};

// Convienence
typedef std::shared_ptr<rogue::protocols::batcher::CoreV2> CoreV2Ptr;
}  // namespace batcher
}  // namespace protocols
}  // namespace rogue
#endif
