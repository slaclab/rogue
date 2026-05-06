/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression: rpp::Transport / rpp::Application destruction is safe after
 * create() but before setController(). The owner ctor (rpp::Core) creates
 * the Transport, then Application instances, and only afterwards calls
 * setController() on each. If any sibling shared_ptr ctor in that chain
 * throws, the partially-constructed Transport/Application is destroyed
 * without ever having had setController() called. The dtor must not
 * dereference the still-null cntl_ / thread_ members.
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

#include <sys/resource.h>

#include <system_error>

#include "doctest/doctest.h"
#include "rogue/GeneralError.h"
#include "rogue/protocols/packetizer/Application.h"
#include "rogue/protocols/packetizer/Transport.h"
#include "rogue/protocols/rssi/Application.h"
#include "rogue/protocols/rssi/Controller.h"
#include "rogue/protocols/rssi/Transport.h"

namespace rpp = rogue::protocols::packetizer;
namespace rpr = rogue::protocols::rssi;

TEST_CASE("rpp::Transport dtor without setController does not crash") {
    rpp::TransportPtr t = rpp::Transport::create();
    // intentionally skip setController(): mimics owner-ctor failure between
    // Transport::create() and setController()
    t.reset();
    CHECK_FALSE(static_cast<bool>(t));
}

TEST_CASE("rpp::Application dtor without setController does not crash") {
    rpp::ApplicationPtr a = rpp::Application::create(0);
    a.reset();
    CHECK_FALSE(static_cast<bool>(a));
}

TEST_CASE("rpr::Application dtor without setController does not crash") {
    rpr::ApplicationPtr a = rpr::Application::create();
    a.reset();
    CHECK_FALSE(static_cast<bool>(a));
}

// Regression: second setController() must throw (overwriting joinable thread_ terminates).
// cntlApp avoids the App<->Controller shared_ptr cycle for clean scope-exit join.
TEST_CASE("rpr::Application::setController rejects second call") {
    rpr::TransportPtr   tran    = rpr::Transport::create();
    rpr::ApplicationPtr cntlApp = rpr::Application::create();
    rpr::ApplicationPtr app     = rpr::Application::create();
    rpr::ControllerPtr  cntl    = rpr::Controller::create(1500, tran, cntlApp, false);

    app->setController(cntl);
    CHECK_THROWS_AS(app->setController(cntl), rogue::GeneralError);
}

// Regression: null controller must throw synchronously (not segfault in worker).
TEST_CASE("rpr::Application::setController rejects null controller") {
    rpr::ApplicationPtr app = rpr::Application::create();
    CHECK_THROWS_AS(app->setController(rpr::ControllerPtr()), rogue::GeneralError);
}

// Regression: thread-ctor failure (EAGAIN) must reset cntl_ to break the
// App<->Controller ref cycle.  Forces EAGAIN via RLIMIT_NPROC.
// Linux-only: Darwin RLIMIT_NPROC limits processes, not threads.
#ifndef __APPLE__
TEST_CASE("rpr::Application::setController unwinds cycle on thread-ctor failure") {
    rpr::TransportPtr   tran = rpr::Transport::create();
    rpr::ApplicationPtr app  = rpr::Application::create();
    rpr::ControllerPtr  cntl = rpr::Controller::create(1500, tran, app, false);

    REQUIRE(cntl.use_count() == 1);
    REQUIRE(app.use_count() == 2);

    rlimit oldLim;
    REQUIRE(getrlimit(RLIMIT_NPROC, &oldLim) == 0);
    rlimit newLim    = oldLim;
    newLim.rlim_cur  = 1;  // below current thread count -> pthread_create EAGAIN
    REQUIRE(setrlimit(RLIMIT_NPROC, &newLim) == 0);

    // Catch std::system_error specifically to pin the thread-ctor unwind path.
    bool threw = false;
    try {
        app->setController(cntl);
    } catch (const std::system_error&) {
        threw = true;
    }

    setrlimit(RLIMIT_NPROC, &oldLim);

    // Bail if RLIMIT_NPROC wasn't enforced on this runner.
    REQUIRE(threw);

    // cntl_ must have been cleared (no extra ref from app->cntl_).
    CHECK_EQ(cntl.use_count(), 1);
    CHECK_EQ(app.use_count(), 2);

    // Dropping cntl releases cntl->app_; app should be sole owner.
    cntl.reset();
    CHECK_EQ(app.use_count(), 1);
}
#endif  // !__APPLE__
