/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    Downstream find_package(Rogue) smoke fixture: a custom stream "base type"
 *    that inverts every payload byte (bitwise NOT) of each frame it receives and
 *    forwards the result downstream.
 *
 *    This single source compiles two ways, selected by the CMake option
 *    -DDOWNSTREAM_NO_PYTHON:
 *      - default (Python): a boost.python module `BitInverter` exposing the
 *        BitInverter stream element, exercised by verify_bit_inversion.py.
 *      - NO_PYTHON: a standalone C++ executable with a main() that pushes a
 *        known frame through the inverter and asserts the bytes came out
 *        inverted, returning non-zero on mismatch.
 *
 *    It is built ONLY against the installed Rogue public headers and the
 *    variables exported by RogueConfig.cmake (ROGUE_INCLUDE_DIRS /
 *    ROGUE_LIBRARIES), so it doubles as CI coverage for templates/RogueConfig.cmake.in.
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

#include <memory>

#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/FrameIterator.h"
#include "rogue/interfaces/stream/FrameLock.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"

namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
    #include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Custom stream element: inverts every payload byte and forwards the frame.
//
// Subclasses both Master and Slave, exactly like rogue's own Filter, so it can
// sit in the middle of a stream pipeline: it accepts a frame as a Slave and
// re-emits it to connected slaves as a Master.
class BitInverter : public ris::Master, public ris::Slave {
  public:
    //! Shared-pointer factory (preferred construction path).
    static std::shared_ptr<BitInverter> create() {
        return std::make_shared<BitInverter>();
    }

    BitInverter() : ris::Master(), ris::Slave() {}
    ~BitInverter() {}

    //! Receive a frame, invert each payload byte in place, forward downstream.
    void acceptFrame(ris::FramePtr frame) override {
        // Hold the frame lock for the duration of the byte access.
        ris::FrameLockPtr lock = frame->lock();

        // XOR every payload byte with 0xFF (bitwise inversion).
        for (auto it = frame->begin(); it != frame->end(); ++it) *it ^= 0xFF;

        // Release the lock before handing the frame to downstream slaves.
        lock->unlock();

        sendFrame(frame);
    }

#ifndef NO_PYTHON
    //! Expose to Python as the BitInverter type.
    static void setup_python() {
        bp::class_<BitInverter, std::shared_ptr<BitInverter>, bp::bases<ris::Master, ris::Slave>, boost::noncopyable>(
            "BitInverter",
            bp::init<>());
        bp::implicitly_convertible<std::shared_ptr<BitInverter>, ris::SlavePtr>();
        bp::implicitly_convertible<std::shared_ptr<BitInverter>, ris::MasterPtr>();
    }
#endif
};

#ifndef NO_PYTHON

//! Python module entry point: `import BitInverter` (import rogue first).
BOOST_PYTHON_MODULE(BitInverter) {
    BitInverter::setup_python();
}

#else

    #include <cstdio>
    #include <mutex>
    #include <vector>

    #include "rogue/interfaces/stream/Pool.h"

//! Minimal sink that captures forwarded frames for inspection.
class CaptureSink : public ris::Slave {
  public:
    CaptureSink() : ris::Slave() {}

    void acceptFrame(ris::FramePtr frame) override {
        std::lock_guard<std::mutex> lock(mutex_);
        frames.push_back(frame);
    }

    std::mutex mutex_;
    std::vector<ris::FramePtr> frames;
};

//! Standalone verification: push known bytes through the inverter, check output.
int main() {
    // Known input and its expected bitwise inversion.
    std::vector<uint8_t> input = {0x00, 0xFF, 0xAA, 0x55, 0x0F, 0xF0};
    std::vector<uint8_t> expected(input.size());
    for (std::size_t i = 0; i < input.size(); ++i) expected[i] = static_cast<uint8_t>(input[i] ^ 0xFF);

    // Build a frame from a pool and fill it with the input bytes.
    auto pool  = std::make_shared<ris::Pool>();
    auto frame = pool->acceptReq(static_cast<uint32_t>(input.size()), false);
    {
        ris::FrameLockPtr lock = frame->lock();
        auto it                = frame->beginWrite();
        ris::toFrame(it, static_cast<uint32_t>(input.size()), input.data());
        frame->setPayload(static_cast<uint32_t>(input.size()));
    }

    // Wire inverter -> capture sink and run the frame through.
    auto inverter = BitInverter::create();
    auto sink     = std::make_shared<CaptureSink>();
    inverter->addSlave(sink);
    inverter->acceptFrame(frame);

    // Validate the captured frame.
    if (sink->frames.size() != 1) {
        printf("FAIL: expected 1 forwarded frame, got %zu\n", sink->frames.size());
        return 1;
    }

    auto out = sink->frames.at(0);
    ris::FrameLockPtr lock = out->lock();
    if (out->getPayload() != input.size()) {
        printf("FAIL: payload size %u != %zu\n", static_cast<unsigned>(out->getPayload()), input.size());
        return 1;
    }

    std::size_t idx = 0;
    for (auto it = out->begin(); it != out->end(); ++it, ++idx) {
        if (*it != expected[idx]) {
            printf("FAIL: byte %zu = 0x%02X, expected 0x%02X\n", idx, *it, expected[idx]);
            return 1;
        }
    }

    printf("PASS: %zu bytes inverted correctly via find_package(Rogue)\n", input.size());
    return 0;
}

#endif
