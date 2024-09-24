/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    SLAC AXI Splitter V1
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
#ifndef __ROGUE_PROTOCOLS_BATCHER_SPLITTER_V1_H__
#define __ROGUE_PROTOCOLS_BATCHER_SPLITTER_V1_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <thread>

#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"

namespace rogue {
namespace protocols {
namespace batcher {

//!  AXI Stream FIFO
class SplitterV1 : public rogue::interfaces::stream::Master, public rogue::interfaces::stream::Slave {
  public:
    //! Class creation
    static std::shared_ptr<rogue::protocols::batcher::SplitterV1> create();

    //! Setup class in python
    static void setup_python();

    //! Creator
    SplitterV1();

    //! Deconstructor
    ~SplitterV1();

    //! Accept a frame from master
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);
};

// Convienence
typedef std::shared_ptr<rogue::protocols::batcher::SplitterV1> SplitterV1Ptr;
}  // namespace batcher
}  // namespace protocols
}  // namespace rogue
#endif
