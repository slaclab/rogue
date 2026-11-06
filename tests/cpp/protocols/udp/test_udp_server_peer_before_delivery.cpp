/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression test for udp::Server learning its peer address before it
 * delivers a received datagram downstream.
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
#include <vector>

#include "doctest/doctest.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/FrameLock.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/protocols/udp/Client.h"
#include "rogue/protocols/udp/Server.h"
#include "support/test_helpers.h"

namespace ris = rogue::interfaces::stream;
namespace rpu = rogue::protocols::udp;

namespace {

// Replies to every frame from inside acceptFrame(), i.e. while the server's
// receive thread is still delivering the datagram being answered.
class EchoSlave : public ris::Slave, public ris::Master {
  public:
    void acceptFrame(ris::FramePtr frame) override {
        std::vector<uint8_t> data;
        {
            ris::FrameLockPtr lock = frame->lock();
            data                   = rogue_test::readFrame(frame, frame->getPayload());
        }
        sendFrame(rogue_test::makeFrame(pool_, data));
    }

  private:
    std::shared_ptr<ris::Pool> pool_ = rogue_test::makePool();
};

}  // namespace

// The server used to forward a datagram before recording its sender, so a
// synchronous reply to the first datagram from a new peer went to the
// previous (initially all-zero) address and was lost.
TEST_CASE("udp::Server replies to the first datagram from a new peer") {
    auto server     = rpu::Server::create(0, false);
    auto client     = rpu::Client::create("127.0.0.1", server->getPort(), false);
    auto echo       = std::make_shared<EchoSlave>();
    auto clientSink = ris::Slave::create();

    server->addSlave(echo);
    echo->addSlave(server);
    client->addSlave(clientSink);

    auto pool = rogue_test::makePool();
    client->acceptFrame(rogue_test::makeFrame(pool, {0x01, 0x02, 0x03, 0x04}));

    const bool echoed = rogue_test::waitUntil([&]() { return clientSink->getFrameCount() > 0; }, 2000);

    client->stop();
    server->stop();

    CHECK_MESSAGE(echoed, "The reply to the first datagram never reached the client");
    CHECK_EQ(clientSink->getByteCount(), 4);
}
