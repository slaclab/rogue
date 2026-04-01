/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Native C++ tests for the low-level memory bit helper routines, covering
 * aligned and unaligned copies, zero-length no-op behavior, cross-byte
 * boundaries, and preservation of untouched bits in destination buffers.
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

#include <array>
#include <vector>

#include "doctest/doctest.h"
#include "rogue/interfaces/memory/Master.h"

namespace {

bool getBit(const std::vector<uint8_t>& data, uint32_t bit) {
    return ((data[bit / 8] >> (bit % 8)) & 0x1U) != 0U;
}

void setBit(std::vector<uint8_t>& data, uint32_t bit, bool value) {
    const uint8_t mask = static_cast<uint8_t>(0x1U << (bit % 8));
    if (value)
        data[bit / 8] |= mask;
    else
        data[bit / 8] &= static_cast<uint8_t>(~mask);
}

std::vector<uint8_t> referenceCopyBits(std::vector<uint8_t> dst,
                                       const std::vector<uint8_t>& src,
                                       uint32_t dstLsb,
                                       uint32_t srcLsb,
                                       uint32_t size) {
    for (uint32_t idx = 0; idx < size; ++idx) setBit(dst, dstLsb + idx, getBit(src, srcLsb + idx));
    return dst;
}

std::vector<uint8_t> referenceSetBits(std::vector<uint8_t> dst, uint32_t lsb, uint32_t size) {
    for (uint32_t idx = 0; idx < size; ++idx) setBit(dst, lsb + idx, true);
    return dst;
}

bool referenceAnyBits(const std::vector<uint8_t>& data, uint32_t lsb, uint32_t size) {
    for (uint32_t idx = 0; idx < size; ++idx) {
        if (getBit(data, lsb + idx)) return true;
    }
    return false;
}

}  // namespace

TEST_CASE("Memory bit helpers handle aligned and unaligned copies") {
    std::vector<uint8_t> src = {0x96, 0x3C, 0xA5, 0xF0};
    std::vector<uint8_t> dst = {0x11, 0x22, 0x33, 0x44};

    auto alignedExpected = referenceCopyBits(dst, src, 8, 8, 16);
    rogue::interfaces::memory::Master::copyBits(dst.data(), 8, src.data(), 8, 16);
    CHECK_EQ(dst, alignedExpected);

    dst = {0xAA, 0x55, 0xAA, 0x55};
    auto unalignedExpected = referenceCopyBits(dst, src, 5, 3, 17);
    rogue::interfaces::memory::Master::copyBits(dst.data(), 5, src.data(), 3, 17);
    CHECK_EQ(dst, unalignedExpected);
}

TEST_CASE("Memory bit helpers preserve buffers for zero-length requests") {
    std::vector<uint8_t> src = {0xFF, 0x00};
    std::vector<uint8_t> dst = {0x12, 0x34};

    rogue::interfaces::memory::Master::copyBits(dst.data(), 0, src.data(), 0, 0);
    CHECK_EQ(dst, std::vector<uint8_t>({0x12, 0x34}));

    rogue::interfaces::memory::Master::setBits(dst.data(), 3, 0);
    CHECK_EQ(dst, std::vector<uint8_t>({0x12, 0x34}));

    CHECK_FALSE(rogue::interfaces::memory::Master::anyBits(dst.data(), 2, 0));
}

TEST_CASE("Memory bit helpers cover set and any across byte boundaries") {
    std::vector<uint8_t> data = {0x00, 0x00, 0x00};
    const auto expected       = referenceSetBits(data, 3, 12);

    rogue::interfaces::memory::Master::setBits(data.data(), 3, 12);
    CHECK_EQ(data, expected);

    CHECK(rogue::interfaces::memory::Master::anyBits(data.data(), 3, 12));
    CHECK_FALSE(rogue::interfaces::memory::Master::anyBits(data.data(), 0, 3));
    CHECK_EQ(rogue::interfaces::memory::Master::anyBits(data.data(), 3, 12), referenceAnyBits(data, 3, 12));
    CHECK_EQ(rogue::interfaces::memory::Master::anyBits(data.data(), 0, 3), referenceAnyBits(data, 0, 3));
}
