/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Audit repro for IFCE-012: Block::addVariables uses a C99-style variable-
 * length array "uint8_t excMask[size_]" on the stack.  VLAs are a C++
 * extension (non-standard C++14), can overflow the stack for large blocks,
 * and are forbidden by the project's C++14 standard constraint.
 *
 * Source-text invariant test: reads Block.cpp and asserts the VLA pattern
 * does NOT appear.  On HEAD it does -> CHECK_MESSAGE fires.
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

#include <fstream>
#include <sstream>
#include <string>

#include "doctest/doctest.h"

#ifndef ROGUE_SRC_DIR
    #define ROGUE_SRC_DIR "."
#endif

static std::string readFile(const std::string& path) {
    std::ifstream f(path);
    if (!f.is_open()) return std::string();
    std::ostringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

TEST_CASE("IFCE-012: Block::addVariables uses VLA uint8_t excMask[size_]") {
    const std::string src = readFile(
        ROGUE_SRC_DIR "/src/rogue/interfaces/memory/Block.cpp");
    REQUIRE_MESSAGE(!src.empty(), "Could not read Block.cpp");

    // The VLA pattern appears as: uint8_t excMask[size_]
    // This is non-standard C++14; GCC/Clang accept it as an extension.
    const bool hasVla = (src.find("uint8_t excMask[size_]") != std::string::npos);
    CHECK_MESSAGE(!hasVla,
                  "IFCE-012: Block::addVariables uses VLA "
                  "uint8_t excMask[size_] (non-standard C++14); should use "
                  "std::vector<uint8_t> excMask(size_, 0) instead");
}
