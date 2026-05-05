/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression tests
 * JtagDriver::xferRel() retries a JTAG transfer up to retry_ times.  The
 * inner try/catch block catches ``rogue::GeneralError&`` with an empty body,
 * silently swallowing the original error across all retry attempts.  After
 * exhausting retries the function throws "Timeout error" instead of the
 * actual cause, losing all diagnostic information about what went wrong.
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
#include <vector>

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

static std::vector<std::string> splitLines(const std::string& src) {
    std::vector<std::string> lines;
    std::istringstream ss(src);
    std::string line;
    while (std::getline(ss, line)) lines.push_back(line);
    return lines;
}

TEST_CASE("JtagDriver::xferRel logs caught GeneralError instead of swallowing") {
    const std::string path =
        std::string(ROGUE_SRC_DIR) + "/src/rogue/protocols/xilinx/JtagDriver.cpp";
    const std::string src = readFile(path);
    REQUIRE_MESSAGE(!src.empty(), "JtagDriver.cpp not found at " << path);

    const auto lines = splitLines(src);

    // Locate the xferRel function definition.
    int xferRelLine = -1;
    for (int i = 0; i < static_cast<int>(lines.size()); ++i) {
        if (lines[i].find("xferRel(") != std::string::npos &&
            lines[i].find("//") == std::string::npos) {
            xferRelLine = i;
            break;
        }
    }
    REQUIRE_MESSAGE(xferRelLine >= 0, "xferRel function not found in JtagDriver.cpp");

    // Find the catch(rogue::GeneralError& [name]) block after xferRel.
    // The fix may name the exception parameter (e.g., 'catch (rogue::GeneralError& e)').
    int catchLine = -1;
    for (int i = xferRelLine; i < static_cast<int>(lines.size()); ++i) {
        const auto& l = lines[i];
        if (l.find("catch") != std::string::npos &&
            l.find("rogue::GeneralError&") != std::string::npos) {
            catchLine = i;
            break;
        }
    }
    REQUIRE_MESSAGE(catchLine >= 0,
        "catch(rogue::GeneralError&) not found in xferRel");

    // Capture the catch block body (up to 6 lines after the catch line) and
    // verify it contains a logging or rethrow statement — not just '{}' or '}'.
    std::string catchBody;
    const int end = static_cast<int>(lines.size()) < catchLine + 6
                        ? static_cast<int>(lines.size())
                        : catchLine + 6;
    for (int i = catchLine; i < end; ++i) catchBody += lines[i] + "\n";

    bool isEmptyCatch = false;
    if (catchBody.find("{}") != std::string::npos) {
        isEmptyCatch = true;
    } else if (catchLine + 1 < static_cast<int>(lines.size())) {
        std::string stripped;
        for (char c : lines[catchLine + 1]) {
            if (c != ' ' && c != '\t') stripped += c;
        }
        if (stripped == "}" || stripped.empty()) isEmptyCatch = true;
    }

    const bool logsOrRethrows =
        catchBody.find("log_") != std::string::npos ||
        catchBody.find("warning") != std::string::npos ||
        catchBody.find("error") != std::string::npos ||
        catchBody.find("throw") != std::string::npos ||
        catchBody.find("e.what()") != std::string::npos;
    const bool catchHandlesError = !isEmptyCatch && logsOrRethrows;

    CHECK_MESSAGE(catchHandlesError,
        " regression: catch(rogue::GeneralError&) in xferRel must log "
        "or rethrow the caught error; fix added log_->warning(...) "
        "in the catch body so callers see the root cause across retries "
        "instead of a generic 'Timeout error'");
}
