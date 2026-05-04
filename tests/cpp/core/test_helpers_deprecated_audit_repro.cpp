/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * rogueStreamTap macro has no [[deprecated]] or
 * __attribute__((deprecated)) annotation in include/rogue/Helpers.h.
 *
 * include/rogue/Helpers.h:27 defines `rogueStreamTap` and documents it
 * with a comment "// Add stream tap, DEPRECATED" but the macro itself
 * carries no compiler-visible deprecation attribute.  Downstream code that
 * calls `rogueStreamTap(...)` compiles silently without any diagnostic even
 * with `-Wall -Wdeprecated-declarations`.
 *
 * This test uses a source-text invariant (100% deterministic): reads
 * Helpers.h and asserts that the `rogueStreamTap` definition contains a
 * `deprecated` annotation keyword.  On HEAD it does not → FAIL fires.
 *
 * A secondary check verifies that the comment marker "DEPRECATED" is
 * present (confirming the author's intent) so the assertion failure message
 * is unambiguous.
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
#include "rogue/Directives.h"

#include <algorithm>
#include <fstream>
#include <string>

#include "doctest/doctest.h"

namespace {

std::string readFile(const std::string& path) {
    std::ifstream f(path);
    if (!f.is_open()) return "";
    return std::string((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
}

/**
 * @brief Extract up to @p max_chars starting at the first occurrence of
 *        @p needle in @p src, or empty string if not found.
 */
std::string extractRegion(const std::string& src, const std::string& needle,
                           size_t max_chars = 120) {
    size_t pos = src.find(needle);
    if (pos == std::string::npos) return "";
    size_t end = std::min(pos + max_chars, src.size());
    return src.substr(pos, end - pos);
}

}  // namespace

TEST_CASE("rogueStreamTap carries a compiler-visible deprecation attribute") {
    // Read Helpers.h and verify the rogueStreamTap definition line contains
    // either [[deprecated]], __attribute__((deprecated)), or
    // _Pragma("deprecated") so that callers receive a compile-time diagnostic.
    //
    // On HEAD:
    //   // Add stream tap, DEPRECATED
    //   #define rogueStreamTap(src, dst) src->addSlave(dst);
    //
    // The fix would add a [[deprecated]] wrapper function or a
    // ROGUE_DEPRECATED macro expansion adjacent to the definition.
    //
    // Discriminator: the 120-char region starting at "rogueStreamTap"
    // should contain "deprecated" in a C++ attribute or GCC attribute form,
    // not merely in a comment.

    const std::string src = readFile(std::string(ROGUE_SRC_DIR) + "/include/rogue/Helpers.h");

    REQUIRE_MESSAGE(!src.empty(),
                    "could not open include/rogue/Helpers.h (ROGUE_SRC_DIR=",
                    ROGUE_SRC_DIR, ")");

    // Secondary: confirm the author's intent comment exists.
    bool has_intent_comment = (src.find("DEPRECATED") != std::string::npos);
    CHECK_MESSAGE(has_intent_comment,
                  "the DEPRECATED comment is absent from Helpers.h; "
                  "test assumption needs revisiting.");

    // Locate the macro definition line.
    std::string tap_region = extractRegion(src, "#define rogueStreamTap");
    REQUIRE_MESSAGE(!tap_region.empty(),
                    "could not locate #define rogueStreamTap in Helpers.h");

    // A compiler-visible deprecation requires one of:
    //   [[deprecated]]              (C++14 standard attribute)
    //   __attribute__((deprecated)) (GCC/Clang extension)
    //   _Pragma("deprecated")       (MSVC-style; not used in rogue)
    bool has_deprecated_attr =
        (tap_region.find("[[deprecated]]")              != std::string::npos) ||
        (tap_region.find("__attribute__((deprecated))") != std::string::npos) ||
        (tap_region.find("_Pragma(\"deprecated\")")     != std::string::npos);

    CHECK_MESSAGE(has_deprecated_attr,
                  "rogueStreamTap is marked DEPRECATED only in a comment; "
                  "the #define carries no [[deprecated]] or __attribute__((deprecated)) "
                  "so callers receive no compile-time diagnostic. "
                  "Replace the macro with a deprecated inline wrapper function or "
                  "add a ROGUE_DEPRECATED macro to the definition.");
}
