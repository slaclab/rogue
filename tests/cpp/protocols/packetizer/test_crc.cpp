/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    Unit tests for rogue/protocols/packetizer/CRC.h
 *-----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to
 * the license terms in the LICENSE.txt file found in the top-level directory
 * of this distribution and at:
 * https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
 * No part of the rogue software platform, including this file, may be
 * copied, modified, propagated, or distributed except according to the terms
 * contained in the LICENSE.txt file.
 *-----------------------------------------------------------------------------
 **/

#include <doctest/doctest.h>

#include <cstdint>
#include <cstring>

#define CRCPP_INCLUDE_ESOTERIC_CRC_DEFINITIONS
#include "rogue/protocols/packetizer/CRC.h"

using CRC = ::CRC;

static const char checkData[] = "123456789";
static const size_t checkLen  = 9;

TEST_CASE("CRC-32 standard check vector") {
    auto result = CRC::Calculate(checkData, checkLen, CRC::CRC_32());
    CHECK_EQ(result, static_cast<uint32_t>(0xCBF43926));
}

TEST_CASE("CRC-32 BZIP2 check vector") {
    auto result = CRC::Calculate(checkData, checkLen, CRC::CRC_32_BZIP2());
    CHECK_EQ(result, static_cast<uint32_t>(0xFC891918));
}

TEST_CASE("CRC-32 MPEG2 check vector") {
    auto result = CRC::Calculate(checkData, checkLen, CRC::CRC_32_MPEG2());
    CHECK_EQ(result, static_cast<uint32_t>(0x0376E6E7));
}

TEST_CASE("CRC-32 POSIX check vector") {
    auto result = CRC::Calculate(checkData, checkLen, CRC::CRC_32_POSIX());
    CHECK_EQ(result, static_cast<uint32_t>(0x765E7680));
}

TEST_CASE("CRC-16 CCITT-FALSE check vector") {
    auto result = CRC::Calculate(checkData, checkLen, CRC::CRC_16_CCITTFALSE());
    CHECK_EQ(result, static_cast<uint16_t>(0x29B1));
}

TEST_CASE("CRC-16 XMODEM check vector") {
    auto result = CRC::Calculate(checkData, checkLen, CRC::CRC_16_XMODEM());
    CHECK_EQ(result, static_cast<uint16_t>(0x31C3));
}

TEST_CASE("CRC-16 ARC check vector") {
    auto result = CRC::Calculate(checkData, checkLen, CRC::CRC_16_ARC());
    CHECK_EQ(result, static_cast<uint16_t>(0xBB3D));
}

TEST_CASE("CRC-8 check vector") {
    auto result = CRC::Calculate(checkData, checkLen, CRC::CRC_8());
    CHECK_EQ(result, static_cast<uint8_t>(0xF4));
}

TEST_CASE("CRC-32 incremental matches one-shot") {
    auto params = CRC::CRC_32();

    // One-shot
    auto oneshot = CRC::Calculate(checkData, checkLen, params);

    // Incremental: split at position 4
    auto partial = CRC::Calculate(checkData, 4, params);
    auto incremental = CRC::Calculate(checkData + 4, checkLen - 4, params, partial);

    CHECK_EQ(oneshot, incremental);
}

TEST_CASE("CRC-16 incremental matches one-shot") {
    auto params = CRC::CRC_16_CCITTFALSE();

    auto oneshot = CRC::Calculate(checkData, checkLen, params);
    auto partial = CRC::Calculate(checkData, 5, params);
    auto incremental = CRC::Calculate(checkData + 5, checkLen - 5, params, partial);

    CHECK_EQ(oneshot, incremental);
}

TEST_CASE("CRC-32 table mode matches direct mode") {
    auto params = CRC::CRC_32();
    CRC::Table<uint32_t, 32> table(params);

    auto direct = CRC::Calculate(checkData, checkLen, params);
    auto tabled = CRC::Calculate(checkData, checkLen, table);

    CHECK_EQ(direct, tabled);
}

TEST_CASE("CRC-16 table mode matches direct mode") {
    auto params = CRC::CRC_16_CCITTFALSE();
    CRC::Table<uint16_t, 16> table(params);

    auto direct = CRC::Calculate(checkData, checkLen, params);
    auto tabled = CRC::Calculate(checkData, checkLen, table);

    CHECK_EQ(direct, tabled);
}

TEST_CASE("CRC-32 incremental with table mode") {
    auto params = CRC::CRC_32();
    CRC::Table<uint32_t, 32> table(params);

    auto oneshot = CRC::Calculate(checkData, checkLen, table);
    auto partial = CRC::Calculate(checkData, 3, table);
    auto incremental = CRC::Calculate(checkData + 3, checkLen - 3, table, partial);

    CHECK_EQ(oneshot, incremental);
}

TEST_CASE("CRC-32 of empty data equals initial XOR") {
    auto params = CRC::CRC_32();
    auto result = CRC::Calculate(static_cast<const void*>(nullptr), 0, params);
    CHECK_EQ(result, static_cast<uint32_t>(0x00000000));
}
