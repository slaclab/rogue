/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Native C++ regression coverage for StreamWriter new-file-only opens. open()
 * used O_RDWR | O_CREAT and the max-size rollover used O_APPEND, so reopening
 * an existing path silently overwrote or appended to a previous session's
 * data. Both paths must now refuse an existing file with rogue::GeneralError
 * and leave that file untouched.
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
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>

#include <fstream>
#include <iterator>
#include <string>
#include <vector>

#include "doctest/doctest.h"
#include "rogue/GeneralError.h"
#include "rogue/utilities/fileio/StreamWriter.h"
#include "rogue/utilities/fileio/StreamWriterChannel.h"
#include "support/test_helpers.h"

namespace ruf = rogue::utilities::fileio;

namespace {

constexpr uint32_t FrameSize = 100;
// Non-raw record = 4 byte size + 4 byte header + payload
constexpr uint32_t RecordSize = FrameSize + 8;

std::string makeTempDir() {
    char path[] = "/tmp/rogue_stream_writer_new_file_XXXXXX";
    REQUIRE(mkdtemp(path) != nullptr);
    return path;
}

std::vector<uint8_t> readAll(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    return std::vector<uint8_t>(std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>());
}

bool exists(const std::string& path) {
    struct stat st;
    return stat(path.c_str(), &st) == 0;
}

void sendFrames(const ruf::StreamWriterPtr& writer, uint32_t count) {
    auto pool = rogue_test::makePool();
    std::vector<uint8_t> payload(FrameSize, 0xA5);
    for (uint32_t i = 0; i < count; ++i) writer->getChannel(0)->acceptFrame(rogue_test::makeFrame(pool, payload));
}

}  // namespace

TEST_CASE("StreamWriter open refuses an existing file and leaves it untouched") {
    const std::string dir  = makeTempDir();
    const std::string path = dir + "/data.dat";

    auto writer = ruf::StreamWriter::create();
    writer->setBufferSize(0);
    writer->open(path);
    sendFrames(writer, 3);
    writer->close();

    const auto original = readAll(path);
    REQUIRE(original.size() == 3 * RecordSize);
    REQUIRE(writer->getFrameCount() == 3);

    CHECK_THROWS_AS(writer->open(path), rogue::GeneralError);
    CHECK_FALSE(writer->isOpen());
    CHECK_EQ(writer->getFrameCount(), 3);
    CHECK_EQ(writer->getTotalSize(), 3 * RecordSize);
    CHECK_EQ(readAll(path), original);

    // A fresh path still opens normally after the error.
    const std::string fresh = dir + "/fresh.dat";
    writer->open(fresh);
    CHECK(writer->isOpen());
    writer->close();
    CHECK(exists(fresh));
}

TEST_CASE("StreamWriter rollover refuses an existing split file") {
    const std::string dir      = makeTempDir();
    const std::string base     = dir + "/split.dat";
    const std::string leftover = base + ".2";

    {
        std::ofstream out(leftover, std::ios::binary);
        out << "leftover from a previous session";
    }
    const auto original = readAll(leftover);

    auto writer = ruf::StreamWriter::create();
    writer->setBufferSize(0);
    writer->setMaxSize(2 * RecordSize);
    writer->open(base);
    sendFrames(writer, 2);
    REQUIRE(writer->getFrameCount() == 2);

    // The third record does not fit in split.dat.1 and must roll to .2
    CHECK_THROWS_AS(sendFrames(writer, 1), rogue::GeneralError);
    CHECK_FALSE(writer->isOpen());
    CHECK_EQ(readAll(leftover), original);
    CHECK_EQ(readAll(base + ".1").size(), 2 * RecordSize);
    CHECK_FALSE(exists(base + ".3"));
    writer->close();
}

TEST_CASE("StreamWriter rollover onto fresh split files still works") {
    const std::string dir  = makeTempDir();
    const std::string base = dir + "/split.dat";

    auto writer = ruf::StreamWriter::create();
    writer->setBufferSize(0);
    writer->setMaxSize(2 * RecordSize);
    writer->open(base);
    sendFrames(writer, 5);
    writer->close();

    CHECK_EQ(readAll(base + ".1").size(), 2 * RecordSize);
    CHECK_EQ(readAll(base + ".2").size(), 2 * RecordSize);
    CHECK_EQ(readAll(base + ".3").size(), 1 * RecordSize);
}
