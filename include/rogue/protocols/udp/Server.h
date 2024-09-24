/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * UDP Server
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
#ifndef __ROGUE_PROTOCOLS_UDP_SERVER_H__
#define __ROGUE_PROTOCOLS_UDP_SERVER_H__
#include "rogue/Directives.h"

#include <netdb.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <stdint.h>
#include <sys/socket.h>

#include <memory>
#include <thread>

#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/protocols/udp/Core.h"

namespace rogue {
namespace protocols {
namespace udp {

//! PGP Card class
class Server : public rogue::protocols::udp::Core,
               public rogue::interfaces::stream::Master,
               public rogue::interfaces::stream::Slave {
    //! Local port number
    uint16_t port_;

    //! Local socket address
    struct sockaddr_in locAddr_;

    //! Thread background
    void runThread(std::weak_ptr<int>);

  public:
    //! Class creation
    static std::shared_ptr<rogue::protocols::udp::Server> create(uint16_t port, bool jumbo);

    //! Setup class in python
    static void setup_python();

    //! Creator
    Server(uint16_t port, bool jumbo);

    //! Destructor
    ~Server();

    //! Stop the interface
    void stop();

    //! Get port number
    uint32_t getPort();

    //! Accept a frame from master
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);
};

// Convenience
typedef std::shared_ptr<rogue::protocols::udp::Server> ServerPtr;

}  // namespace udp
}  // namespace protocols
};  // namespace rogue

#endif
