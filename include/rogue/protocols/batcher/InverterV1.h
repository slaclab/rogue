/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *   SLAC AXI Inverter V1
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
#ifndef ROGUE_PROTOCOLS_BATCHER_INVERTERV1_H
#define ROGUE_PROTOCOLS_BATCHER_INVERTERV1_H
#include "rogue/Directives.h"


#include <memory>
#include <thread>

#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"

namespace rogue {
namespace protocols {
namespace batcher {

//!  AXI Stream FIFO
class InverterV1 : public rogue::interfaces::stream::Master, public rogue::interfaces::stream::Slave {
  public:
    //! Class creation
    static std::shared_ptr<rogue::protocols::batcher::InverterV1> create();

    //! Setup class in python
    static void setup_python();

    //! Creator
    InverterV1();

    //! Deconstructor
    ~InverterV1();

    //! Accept a frame from master
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);
};

// Convienence
typedef std::shared_ptr<rogue::protocols::batcher::InverterV1> InverterV1Ptr;
}  // namespace batcher
}  // namespace protocols
}  // namespace rogue
#endif
