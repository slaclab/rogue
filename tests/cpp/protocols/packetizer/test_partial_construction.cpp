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

#include "doctest/doctest.h"
#include "rogue/protocols/packetizer/Application.h"
#include "rogue/protocols/packetizer/Transport.h"
#include "rogue/protocols/rssi/Application.h"

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
