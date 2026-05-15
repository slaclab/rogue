/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Functional regression test for memory::TcpServer response socket recovery
 * after a failed multipart zmq_sendmsg().
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
#include <zmq.h>

#include <unistd.h>

#include <atomic>
#include <cerrno>
#include <cstdlib>
#include <memory>
#include <string>

#include "doctest/doctest.h"
#include "rogue/GeneralError.h"
#include "rogue/interfaces/memory/Constants.h"
#include "rogue/interfaces/memory/Emulate.h"
#include "rogue/interfaces/memory/Master.h"
#include "rogue/interfaces/memory/TcpClient.h"
#include "rogue/interfaces/memory/TcpServer.h"

namespace rim = rogue::interfaces::memory;

namespace {

struct ServerWithPort {
    std::shared_ptr<class SendFailureTcpServer> server;
    uint16_t port;
};

class SendFailureTcpServer : public rim::TcpServer {
  public:
    SendFailureTcpServer(const std::string& addr, uint16_t port) : rim::TcpServer(addr, port) {}

    void failNextResponseAtPart(uint32_t part) {
        failPart_.store(part);
        failed_.store(false);
        armed_.store(true);
        currentPart_.store(0);
    }

    bool failed() const {
        return failed_.load();
    }

  protected:
    int sendResponseMsg_(void* msg, int flags) override {
        if (armed_.load() && !failed_.load()) {
            const uint32_t part = currentPart_.load();
            if (part == failPart_.load()) {
                failed_.store(true);
                currentPart_.store(0);
                errno = EAGAIN;
                return -1;
            }
        }

        const int ret = rim::TcpServer::sendResponseMsg_(msg, flags);
        if (armed_.load() && !failed_.load()) {
            currentPart_.store((ret >= 0 && (flags & ZMQ_SNDMORE) != 0) ? currentPart_.load() + 1 : 0);
        }
        return ret;
    }

  private:
    std::atomic<bool> armed_{false};
    std::atomic<bool> failed_{false};
    std::atomic<uint32_t> failPart_{0};
    std::atomic<uint32_t> currentPart_{0};
};

ServerWithPort createServerOnAvailablePort() {
    const uint16_t start = static_cast<uint16_t>(20000 + ((getpid() % 200) * 128));

    for (uint32_t offset = 0; offset < 128; offset += 2) {
        const uint16_t port = static_cast<uint16_t>(start + offset);
        try {
            return {std::make_shared<SendFailureTcpServer>("127.0.0.1", port), port};
        } catch (const rogue::GeneralError&) {
            continue;
        }
    }

    FAIL("Could not create memory::TcpServer on an available TCP port pair");
    return {nullptr, 0};
}

}  // namespace

TEST_CASE("TcpServer rebuilds response socket after multipart send failure") {
    auto memory = rim::Emulate::create(4, 0x1000);
    auto serverWithPort = createServerOnAvailablePort();
    auto server         = serverWithPort.server;
    server->setSlave(memory);

    auto client = rim::TcpClient::create("127.0.0.1", serverWithPort.port, false);
    REQUIRE(client->waitReady(3.0, 0.05));

    auto master = rim::Master::create();
    master->setSlave(client);
    master->setTimeout(250000);

    server->failNextResponseAtPart(2);

    uint32_t firstRead = 0;
    uint32_t id        = master->reqTransaction(0x20, sizeof(firstRead), &firstRead, rim::Read);
    master->waitTransaction(id);

    const std::string firstError = master->getError();
    INFO("First transaction result: " << firstError);
    CHECK(firstError.find("Timeout waiting for register transaction") != std::string::npos);
    CHECK(server->failed());
    master->clearError();

    uint32_t writeValue = 0x5AA55AA5;
    id = master->reqTransaction(0x20, sizeof(writeValue), &writeValue, rim::Write);
    master->waitTransaction(id);
    std::string error = master->getError();
    INFO("Write after response socket rebuild result: " << error);
    CHECK(error.empty());
    master->clearError();

    uint32_t readValue = 0;
    id = master->reqTransaction(0x20, sizeof(readValue), &readValue, rim::Read);
    master->waitTransaction(id);
    error = master->getError();
    INFO("Read after response socket rebuild result: " << error);
    CHECK(error.empty());
    CHECK_EQ(readValue, writeValue);

    client->stop();
    server->stop();
}
