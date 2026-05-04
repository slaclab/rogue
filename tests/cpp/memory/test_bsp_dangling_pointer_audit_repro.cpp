/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression tests for two missing/incomplete binding and pointer-safety issues:
 *   stream::TcpClient setup_python does not expose the _start()
 *             lifecycle hook or the deprecated close() alias; the binding is
 *             incomplete relative to TcpCore
 *   Bsp (C++ API wrapper) stores the Python node via
 *             boost::python::object _obj but the surrounding C++ code stores
 *             a dangling raw char* via bp::extract<char*> without
 *             keeping the Python object alive; or the semantics rely on the
 *             Python root staying alive externally with no contract enforcement
 *
 * Source-text invariant tests; each TEST_CASE asserts a structural property
 * that the fixed code must satisfy.
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

TEST_CASE("stream::TcpClient setup_python missing _start / close binding") {
    const std::string src = readFile(
        ROGUE_SRC_DIR "/src/rogue/interfaces/stream/TcpClient.cpp");
    REQUIRE_MESSAGE(!src.empty(),
                    "Could not read stream/TcpClient.cpp");

    // Locate the setup_python block in TcpClient.cpp
    const std::size_t pos = src.find("TcpClient::setup_python");
    REQUIRE_MESSAGE(pos != std::string::npos,
                    "setup_python not found in stream/TcpClient.cpp");

    // Extract the setup_python body (400 bytes)
    const std::string region = src.substr(pos, 400);

    // FIXED state: setup_python exposes at least one lifecycle hook:
    // - "_start" (the preferred modern name) or
    // - "close" (the deprecated alias) or
    // - "_stop"
    const bool exposesLifecycle = (
        region.find("_start") != std::string::npos  ||
        region.find("_stop") != std::string::npos   ||
        region.find("\"close\"") != std::string::npos ||
        region.find("\"start\"") != std::string::npos ||
        region.find("\"stop\"") != std::string::npos);

    CHECK_MESSAGE(exposesLifecycle,
                  "stream::TcpClient setup_python does not expose "
                  "the _start() lifecycle hook or the deprecated close() alias; "
                  "Python users cannot manage the stream TcpClient lifecycle "
                  "through the TcpClient class directly");
}

TEST_CASE("Bsp uses raw char* extract from bp::object without RAII") {
    const std::string src = readFile(
        ROGUE_SRC_DIR "/src/rogue/interfaces/api/Bsp.cpp");
    REQUIRE_MESSAGE(!src.empty(), "Could not read interfaces/api/Bsp.cpp");

    // Bsp::operator[] returns a Bsp by value constructed from
    // a bp::object obtained via getNode(name).  This means the node object
    // has its reference count managed via the stack-local bp::object inside
    // operator[], not by any persistent owner.  A caller that holds a Bsp
    // after the Python root is destroyed will have a dangling reference.
    //
    // The fix is to hold a std::shared_ptr to the node or to wrap the Bsp
    // in shared_ptr semantics.  The structural assertion: Bsp::_name is set
    // via "bp::extract<char*>(_obj.attr("name"))" -- extracting a raw char*
    // which can dangle if the Python object's string storage is GC'd.
    // The fix stores _name using std::string(bp::extract<std::string>(...)).
    //
    // On HEAD: "bp::extract<char*>" is used to set _name.
    const bool hasRawCharExtract =
        (src.find("extract<char*>") != std::string::npos);
    CHECK_MESSAGE(!hasRawCharExtract,
                  "Bsp stores _name via bp::extract<char*> which "
                  "yields a raw char* pointing into a Python string object; "
                  "if the Python string is GC'd the pointer dangles; "
                  "should use bp::extract<std::string> to own the copy");
}
