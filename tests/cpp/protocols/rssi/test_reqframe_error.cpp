/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression: rpr::Controller::reqFrame() reports the actual buffer size and
 * the header size in the correct order when the transport returns a buffer
 * too small to hold the RSSI header.
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
#include <stdint.h>

#include <memory>
#include <string>

#include "doctest/doctest.h"

#include "rogue/GeneralError.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/protocols/rssi/Application.h"
#include "rogue/protocols/rssi/Controller.h"
#include "rogue/protocols/rssi/Header.h"
#include "rogue/protocols/rssi/Transport.h"

namespace ris = rogue::interfaces::stream;
namespace rpr = rogue::protocols::rssi;

namespace {

// Controller outlives the endpoints in this test; the deleter is a no-op so
// the back-references do not form a shared_ptr cycle.
template <class T>
std::shared_ptr<T> borrowed(const std::shared_ptr<T>& object) {
    return std::shared_ptr<T>(object.get(), [](T*) {});
}

}  // namespace

TEST_CASE("rpr::Controller::reqFrame reports buffer size and header size in order") {
    const uint32_t smallSize = 4;

    rpr::TransportPtr transport     = rpr::Transport::create();
    rpr::ApplicationPtr application = rpr::Application::create();
    rpr::ControllerPtr controller   = rpr::Controller::create(1024, borrowed(transport), borrowed(application), false);

    // Downstream slave hands back fixed 4-byte buffers, smaller than HeaderSize.
    ris::SlavePtr sink = ris::Slave::create();
    sink->setFixedSize(smallSize);
    transport->addSlave(sink);

    REQUIRE(smallSize < static_cast<uint32_t>(rpr::Header::HeaderSize));

    std::string message;
    try {
        controller->reqFrame(16);
    } catch (const rogue::GeneralError& e) {
        message = e.what();
    }

    const std::string expected = "Buffer size " + std::to_string(smallSize) + " is less than min header size " +
                                 std::to_string(rpr::Header::HeaderSize);
    INFO("actual message: " << message);
    CHECK(message.find(expected) != std::string::npos);
}
