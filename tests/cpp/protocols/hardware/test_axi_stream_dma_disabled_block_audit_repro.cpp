/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Audit repro for HW-010:
 * AxiStreamDma.cpp runThread() contains a ``#if 0 ... #else ... #endif``
 * block where the disabled branch implements bulk DMA buffer return via
 * dmaReturnIoctl().  The active ``#else`` branch does per-buffer returns.
 * The disabled code is left in-tree with no comment explaining why it was
 * disabled, when it would be re-enabled, or whether it was tested.
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

static std::string readFile(const std::string& path) {
    std::ifstream f(path);
    if (!f.is_open()) return "";
    std::ostringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

TEST_CASE("HW-010: AxiStreamDma.cpp has no unexplained #if 0 disabled block") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/hardware/axi/AxiStreamDma.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "AxiStreamDma.cpp not found at " << path);

    const bool hasIf0 = src.find("#if 0") != std::string::npos;
    CHECK_MESSAGE(!hasIf0,
        "HW-010 regression: '#if 0' is back in AxiStreamDma.cpp; fix(HW-010) "
        "removed the disabled bulk-DMA block (dmaReturnIoctl path) that had "
        "no comment explaining why it was disabled. If a #if 0 block is "
        "needed again, replace it with a comment explaining the intent and "
        "linking to a tracking issue");
}
