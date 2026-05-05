/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression test ensuring every zmq_sendmsg() call in
 * memory::TcpServer::runThread has its return value checked.  Previously
 * the send loop called zmq_sendmsg() six times ignoring the return value;
 * a partial multi-part failure left the PUSH socket in an undefined state
 * without any error propagation.
 *
 * Source-text invariant test: reads TcpServer.cpp and verifies each
 * zmq_sendmsg call has a return-code check.
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

// Replace C/C++ line comments, block comments, string literals, and char
// literals with spaces (preserving newlines).  Without this, a future
// commit that adds a comment or log message containing "zmq_sendmsg(" --
// e.g. `// zmq_sendmsg(...) was the call we hardened` -- would be picked
// up by the scan below as a "call site" and trip a false unchecked
// failure.  This is a deliberately small pre-processor; it is sufficient
// for the source files this audit-repro inspects, not a full C++ tokeniser.
static std::string stripCommentsAndStrings(const std::string& src) {
    std::string out;
    out.reserve(src.size());
    enum { CODE, LINE_CMT, BLOCK_CMT, STR_LIT, CHR_LIT } state = CODE;
    for (std::size_t i = 0; i < src.size(); ++i) {
        const char c = src[i];
        const char n = (i + 1 < src.size()) ? src[i + 1] : '\0';
        switch (state) {
            case CODE:
                if (c == '/' && n == '/') {
                    out += "  ";
                    ++i;
                    state = LINE_CMT;
                } else if (c == '/' && n == '*') {
                    out += "  ";
                    ++i;
                    state = BLOCK_CMT;
                } else if (c == '"') {
                    out += ' ';
                    state = STR_LIT;
                } else if (c == '\'') {
                    out += ' ';
                    state = CHR_LIT;
                } else {
                    out += c;
                }
                break;
            case LINE_CMT:
                if (c == '\n') {
                    out += '\n';
                    state = CODE;
                } else {
                    out += ' ';
                }
                break;
            case BLOCK_CMT:
                if (c == '*' && n == '/') {
                    out += "  ";
                    ++i;
                    state = CODE;
                } else if (c == '\n') {
                    out += '\n';
                } else {
                    out += ' ';
                }
                break;
            case STR_LIT:
                if (c == '\\' && n != '\0') {
                    out += "  ";
                    ++i;
                } else if (c == '"') {
                    out += ' ';
                    state = CODE;
                } else if (c == '\n') {
                    out += '\n';
                } else {
                    out += ' ';
                }
                break;
            case CHR_LIT:
                if (c == '\\' && n != '\0') {
                    out += "  ";
                    ++i;
                } else if (c == '\'') {
                    out += ' ';
                    state = CODE;
                } else if (c == '\n') {
                    out += '\n';
                } else {
                    out += ' ';
                }
                break;
        }
    }
    return out;
}

// Locate every occurrence of `needle` in `hay`, and for each one decide
// whether the surrounding source text places the call in a "checked" context
// (assignment to a variable, used as part of an if/while predicate, or
// returned to the caller).  A single bare statement counts as unchecked.
//
// `hay` is expected to have already had comments and string literals
// elided by stripCommentsAndStrings(), so matches inside `// ...` or
// `"..."` cannot trigger spurious failures.
static bool everyCallIsChecked(const std::string& hay, const std::string& needle) {
    if (hay.find(needle) == std::string::npos) return false;

    auto isIdent = [](char c) {
        return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
               (c >= '0' && c <= '9') || c == '_';
    };

    std::size_t pos = 0;
    while ((pos = hay.find(needle, pos)) != std::string::npos) {
        // Walk back through whitespace to the previous non-space character.
        std::size_t i = pos;
        while (i > 0 && (hay[i - 1] == ' ' || hay[i - 1] == '\t' || hay[i - 1] == '\n')) {
            --i;
        }
        // Acceptable preceding single-char contexts:
        //   "= zmq_sendmsg("   (return code captured)
        //   "(zmq_sendmsg("    (used inside an expression / predicate)
        //   "!zmq_sendmsg("    (boolean negation as predicate)
        // and a few binary/ternary operator characters that can introduce
        // a sub-expression.
        const char prev = (i > 0) ? hay[i - 1] : '\0';
        const bool prevOp = (prev == '=' || prev == '(' || prev == '!' ||
                             prev == '<' || prev == '>' || prev == ',' ||
                             prev == '?' || prev == ':' || prev == '|' ||
                             prev == '&');
        // Acceptable preceding keyword: `return zmq_sendmsg(...)`.  Walk
        // back through identifier chars and check that the token is `return`.
        bool prevReturn = false;
        if (!prevOp && i > 0 && isIdent(hay[i - 1])) {
            std::size_t j = i;
            while (j > 0 && isIdent(hay[j - 1])) --j;
            prevReturn = (i - j == 6 && hay.compare(j, 6, "return") == 0);
        }
        if (!prevOp && !prevReturn) return false;
        pos += needle.size();
    }
    return true;
}

TEST_CASE("TcpServer runThread send loop checks zmq_sendmsg returns") {
    const std::string raw = readFile(
        ROGUE_SRC_DIR "/src/rogue/interfaces/memory/TcpServer.cpp");
    REQUIRE_MESSAGE(!raw.empty(), "Could not read memory/TcpServer.cpp");

    // Confirm the call exists at all (raw scan, before stripping)
    REQUIRE_MESSAGE(raw.find("zmq_sendmsg") != std::string::npos,
                    "zmq_sendmsg not found in memory/TcpServer.cpp");

    // Strip comments and string/char literals so that documentation or log
    // messages mentioning "zmq_sendmsg(" cannot be mistaken for call sites.
    const std::string src = stripCommentsAndStrings(raw);

    // Every zmq_sendmsg call in the entire translation unit must be in a
    // checked context.  This is stronger than a single nearby-window check:
    // a partial fix that wraps one call in an if() while leaving five other
    // bare calls in an unrolled loop will fail this assertion, even though
    // the old window-based scan would have accepted it.
    const bool allChecked = everyCallIsChecked(src, "zmq_sendmsg(");

    CHECK_MESSAGE(allChecked,
                  "TcpServer runThread send loop ignores "
                  "zmq_sendmsg return code; partial multi-part message "
                  "leaves PUSH socket in undefined state without error "
                  "propagation to caller (every zmq_sendmsg call in the "
                  "file must be assigned, predicated, or otherwise "
                  "consumed -- bare-statement calls are not accepted)");
}
