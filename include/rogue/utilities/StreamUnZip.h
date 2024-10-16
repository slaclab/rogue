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
#ifndef ROGUE_UTILITIES_STREAMUNZIP_H
#define ROGUE_UTILITIES_STREAMUNZIP_H
#include "rogue/Directives.h"


#include <memory>
#include <thread>

#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"

namespace rogue {
namespace utilities {

//! Stream compressor
class StreamUnZip : public rogue::interfaces::stream::Slave, public rogue::interfaces::stream::Master {
  public:
    //! Class creation
    static std::shared_ptr<rogue::utilities::StreamUnZip> create();

    //! Setup class in python
    static void setup_python();

    //! Creator
    StreamUnZip();

    //! Deconstructor
    ~StreamUnZip();

    //! Accept a frame from master
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    //! Accept a new frame request
    std::shared_ptr<rogue::interfaces::stream::Frame> acceptReq(uint32_t size, bool zeroCopyEn);
};

// Convenience
typedef std::shared_ptr<rogue::utilities::StreamUnZip> StreamUnZipPtr;
}  // namespace utilities
}  // namespace rogue
#endif
