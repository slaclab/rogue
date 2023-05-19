/**
 *-----------------------------------------------------------------------------
 * Title      : XVC Server Class
 * ----------------------------------------------------------------------------
 * Description:
 * Rogue implementation of the XVC Server
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
#ifndef __ROGUE_PROTOCOLS_XILINX_XVC_H__
#define __ROGUE_PROTOCOLS_XILINX_XVC_H__
#include <netdb.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <stdint.h>
#include <sys/socket.h>

#include <memory>
#include <thread>

#include <rogue/Directives.h>
#include <rogue/GeneralError.h>
#include <rogue/Logging.h>
#include <rogue/Queue.h>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/protocols/xilinx/JtagDriver.h>
#include <rogue/protocols/xilinx/XvcConnection.h>
#include <rogue/protocols/xilinx/XvcServer.h>

namespace rogue {
namespace protocols {
namespace xilinx {
const unsigned int kMaxArgs = 3;

class Xvc : public rogue::interfaces::stream::Master,
            public rogue::interfaces::stream::Slave,
            public rogue::protocols::xilinx::JtagDriver {
  protected:
    unsigned mtu_;

    // Use rogue frames to exchange data with other rogue objects
    rogue::Queue<std::shared_ptr<rogue::interfaces::stream::Frame>> queue_;

    // Log
    std::shared_ptr<rogue::Logging> log_;

    //! Thread background
    std::thread* thread_;
    bool threadEn_;

    // Lock
    std::mutex mtx_;

    // TCP server for Vivado client
    void runThread();

  public:
    //! Class creation
    static std::shared_ptr<rogue::protocols::xilinx::Xvc> create(uint16_t port);

    //! Setup class in python
    static void setup_python();

    //! Creator
    Xvc(uint16_t port);

    //! Destructor
    ~Xvc();

    //! Start the interface
    void start();

    //! Stop the interface
    void stop();

    // Receive frame
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    virtual unsigned long getMaxVectorSize() final;

    virtual int xfer(uint8_t* txBuffer,
                     unsigned txBytes,
                     uint8_t* hdBuffer,
                     unsigned hdBytes,
                     uint8_t* rxBuffer,
                     unsigned rxBytes) final;
};

// Convenience
typedef std::shared_ptr<rogue::protocols::xilinx::Xvc> XvcPtr;
}  // namespace xilinx
}  // namespace protocols
}  // namespace rogue

#endif
