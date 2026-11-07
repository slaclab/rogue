/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression: releasing an rpr::Client or rpr::Server frees its Controller,
 * Transport and Application. The endpoints hold only weak references back to
 * the Controller, so no shared_ptr cycle keeps them (and the RssiApp thread)
 * alive after the owner is gone.
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
#include <memory>

#include "doctest/doctest.h"

#include "rogue/GeneralError.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/protocols/rssi/Application.h"
#include "rogue/protocols/rssi/Client.h"
#include "rogue/protocols/rssi/Server.h"
#include "rogue/protocols/rssi/Transport.h"

namespace rpr = rogue::protocols::rssi;

namespace {

template <class T>
void checkReleased() {
    std::weak_ptr<rpr::Application> app;
    std::weak_ptr<rpr::Transport> tran;
    {
        std::shared_ptr<T> owner = T::create(1024);
        app                      = owner->application();
        tran                     = owner->transport();
        owner->start();
        REQUIRE_FALSE(app.expired());
        REQUIRE_FALSE(tran.expired());
    }
    CHECK(app.expired());
    CHECK(tran.expired());
}

}  // namespace

TEST_CASE("rpr::Client release frees Application and Transport") {
    checkReleased<rpr::Client>();
}

TEST_CASE("rpr::Server release frees Application and Transport") {
    checkReleased<rpr::Server>();
}

TEST_CASE("rpr::Application outliving its Client is inert") {
    rpr::ApplicationPtr app;
    rpr::TransportPtr tran;
    {
        rpr::ClientPtr client = rpr::Client::create(1024);
        app                   = client->application();
        tran                  = client->transport();
    }

    // Frames into orphaned endpoints are dropped; allocation reports an error.
    CHECK_NOTHROW(tran->acceptFrame(rogue::interfaces::stream::Frame::create()));
    CHECK_NOTHROW(app->acceptFrame(rogue::interfaces::stream::Frame::create()));
    CHECK_THROWS_AS(app->acceptReq(16, false), rogue::GeneralError);
}
