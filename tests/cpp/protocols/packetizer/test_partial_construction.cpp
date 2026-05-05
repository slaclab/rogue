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

// Regression: a second setController() call must throw rogue::GeneralError
// instead of silently overwriting the still-joinable thread_ unique_ptr,
// which would invoke std::terminate() on the running worker.
//
// `cntlApp` is a separate, never-set-up Application passed to
// Controller::create() so the Controller's app_ does not point back at the
// Application under test.  This avoids the Application<->Controller
// shared_ptr cycle (app->cntl_ <-> cntl->app_) that would otherwise pin
// both objects past scope exit and leak the running worker thread.  The
// Application under test (`app`) holds the Controller via setController()
// and its destructor stops/joins the worker cleanly at scope exit.
TEST_CASE("rpr::Application::setController rejects second call") {
    rpr::TransportPtr   tran    = rpr::Transport::create();
    rpr::ApplicationPtr cntlApp = rpr::Application::create();
    rpr::ApplicationPtr app     = rpr::Application::create();
    rpr::ControllerPtr  cntl    = rpr::Controller::create(1500, tran, cntlApp, false);

    app->setController(cntl);
    CHECK_THROWS_AS(app->setController(cntl), rogue::GeneralError);
}

// Regression: setController() must reject a null controller synchronously
// at the wiring site instead of storing it and starting the worker thread,
// which would dereference cntl_ in runThread()/acceptReq()/acceptFrame()
// and turn a caller mistake into an asynchronous segfault.
TEST_CASE("rpr::Application::setController rejects null controller") {
    rpr::ApplicationPtr app = rpr::Application::create();
    CHECK_THROWS_AS(app->setController(rpr::ControllerPtr()), rogue::GeneralError);
    // After the throw, no worker has been started, so destruction of `app`
    // at scope exit must remain safe (mirrors the existing
    // "dtor without setController" coverage above).
}

// Regression: when std::thread construction inside setController() throws
// (pthread_create EAGAIN under thread-table pressure), the catch block
// MUST reset cntl_ before re-throwing so Application does not retain a
// strong reference to Controller while Controller's app_ still points
// back at this Application -- a cycle with no worker to ever join would
// pin both objects in memory.
//
// Force the throw deterministically by lowering RLIMIT_NPROC below the
// current process's thread count: pthread_create then returns EAGAIN and
// std::thread's ctor throws std::system_error.  RLIMIT_NPROC is per-UID
// and per-thread on Linux, so we restore it on every exit path so doctest's
// own teardown and subsequent TEST_CASEs do not run with the lowered limit.
//
// Linux-only: Darwin's RLIMIT_NPROC limits processes per-UID, not threads,
// so lowering it does not gate pthread_create on macOS.  If we ran this on
// Darwin, app->setController(cntl) would succeed despite our intent, the
// cycle (app->cntl_ <-> cntl->app_) would never be unwound, and the test
// would leak both objects plus a live worker thread into the rest of the
// ctest process.  See rogue_ci.yml: macOS CI runs `ctest -L cpp`, so the
// gate must exist at compile time.
//
// This test wires app + cntl with the production cross-coupling
// (Controller::app_ = app, app->cntl_ set by setController on success),
// which is the exact configuration where a missed unwind leaks both
// objects in a strong-reference cycle.  Earlier tests in this file
// deliberately use a separate cntlApp to avoid the cycle for cases where
// setController succeeds and the worker would need to be joined; here
// we WANT the cycle to be observable so we can verify the unwind breaks
// it.
#ifndef __APPLE__
TEST_CASE("rpr::Application::setController unwinds cycle on thread-ctor failure") {
    rpr::TransportPtr   tran = rpr::Transport::create();
    rpr::ApplicationPtr app  = rpr::Application::create();
    rpr::ControllerPtr  cntl = rpr::Controller::create(1500, tran, app, false);

    // Baseline: cntl held only by our local ptr; app held by our local
    // ptr plus cntl->app_ wired in Controller::Controller.  These pin
    // the expected post-unwind use_counts below.
    REQUIRE(cntl.use_count() == 1);
    REQUIRE(app.use_count() == 2);

    rlimit oldLim;
    REQUIRE(getrlimit(RLIMIT_NPROC, &oldLim) == 0);
    rlimit newLim    = oldLim;
    newLim.rlim_cur  = 1;  // below current thread count -> pthread_create EAGAIN
    REQUIRE(setrlimit(RLIMIT_NPROC, &newLim) == 0);

    // Catch std::system_error specifically: that is what std::thread's
    // ctor throws when pthread_create returns EAGAIN, so this catch type
    // pins the regression to the thread-construction unwind path.  An
    // earlier throw site (the null-controller or double-call rejections,
    // which throw rogue::GeneralError) would not satisfy this catch, the
    // exception would propagate, and doctest would report the unexpected
    // exception as a test failure -- which is the behavior we want if a
    // future change makes setController() throw before the std::thread
    // ctor.
    bool threw = false;
    try {
        app->setController(cntl);
    } catch (const std::system_error&) {
        threw = true;
    }

    // Restore RLIMIT_NPROC BEFORE assertions so a CHECK failure that
    // aborts the binary does not leave the lowered limit in place for
    // doctest's own teardown allocations.
    setrlimit(RLIMIT_NPROC, &oldLim);

    // REQUIRE (not CHECK): if pthread_create did not actually return
    // EAGAIN on this runner (e.g., RLIMIT_NPROC was not enforced for the
    // current UID), bail out of this TEST_CASE now.  Continuing would
    // (a) report a cascade of misleading post-unwind invariant failures
    // against a setController() that actually succeeded, and (b) leave
    // the wired app<->cntl cycle live for the remainder of the test
    // body.  Application::~Application joins the worker at scope exit
    // in either case, so doctest's per-case unwind still cleans up.
    REQUIRE(threw);

    // Post-unwind invariants:
    //   - cntl.use_count() must remain 1 (just our local ptr).  If the
    //     catch's cntl_.reset() did not run, app->cntl_ would still hold
    //     cntl and use_count would be 2.
    //   - app.use_count() must remain 2 (our local ptr + cntl->app_).
    //     The unwind does not need to touch this back-ref; clean
    //     destruction comes from dropping cntl, which drops cntl->app_.
    CHECK_EQ(cntl.use_count(), 1);
    CHECK_EQ(app.use_count(), 2);

    // Final invariant: dropping cntl must let app go.  ~Controller()
    // calls stop(), which is a no-op because Controller::start() was
    // never called, so cntl destruction completes synchronously and
    // releases cntl->app_.  If the catch had been bypassed, app->cntl_
    // would pin cntl past our local cntl.reset() and app would still
    // be at use_count 2.
    cntl.reset();
    CHECK_EQ(app.use_count(), 1);
}
#endif  // !__APPLE__
