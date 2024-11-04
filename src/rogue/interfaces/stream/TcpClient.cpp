/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Stream Network Client
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
#include "rogue/Directives.h"

#include "rogue/interfaces/stream/TcpClient.h"

#include <zmq.h>

#include <memory>
#include <string>

#include "rogue/GeneralError.h"
#include "rogue/GilRelease.h"
#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Buffer.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/FrameIterator.h"
#include "rogue/interfaces/stream/FrameLock.h"

namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
    #include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Class creation
ris::TcpClientPtr ris::TcpClient::create(std::string addr, uint16_t port) {
    ris::TcpClientPtr r = std::make_shared<ris::TcpClient>(addr, port);
    return (r);
}

//! Creator
ris::TcpClient::TcpClient(std::string addr, uint16_t port) : ris::TcpCore(addr, port, false) {}

//! Destructor
ris::TcpClient::~TcpClient() {}

void ris::TcpClient::setup_python() {
#ifndef NO_PYTHON

    bp::class_<ris::TcpClient, ris::TcpClientPtr, bp::bases<ris::TcpCore>, boost::noncopyable>(
        "TcpClient",
        bp::init<std::string, uint16_t>());

    bp::implicitly_convertible<ris::TcpClientPtr, ris::TcpCorePtr>();
#endif
}
