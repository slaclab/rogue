/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Audit repro for PROT-019:
 * rssi/Controller.cpp is a 979-line monolith containing state machine,
 * retransmit logic, flow control, out-of-order queue, and timer management
 * all in a single file.  This marker test fails while the file exceeds the
 * refactoring threshold of 600 lines.
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

#include <fstream>
#include <sstream>
#include <string>

#include "doctest/doctest.h"

#ifndef ROGUE_SRC_DIR
    #error "ROGUE_SRC_DIR must be defined via target_compile_definitions"
#endif

// Line-count threshold above which the file is considered a fragility risk.
static const int kMonolithThreshold = 600;

static int countLines(const std::string& src) {
    int n = 0;
    for (char c : src) {
        if (c == '\n') ++n;
    }
    return n;
}

TEST_CASE("PROT-019: rssi/Controller.cpp exceeds 600-line monolith threshold") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/protocols/rssi/Controller.cpp";
    std::ifstream f(path);
    REQUIRE_MESSAGE(f.is_open(), "Controller.cpp not found at " << path);
    std::ostringstream ss;
    ss << f.rdbuf();
    const std::string src = ss.str();
    REQUIRE(!src.empty());

    const int lineCount = countLines(src);

    CHECK_MESSAGE(lineCount < kMonolithThreshold,
        "PROT-019 regression: Controller.cpp has " << lineCount << " lines "
        "(threshold: " << kMonolithThreshold << "); fix(PROT-019) split the "
        "979-line monolith into Controller.cpp + ControllerImpl.hpp; if it "
        "grew back over " << kMonolithThreshold << " lines, split it again");
}
