/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * rogueStreamTap macro has no [[deprecated]] or
 * __attribute__((deprecated)) annotation in include/rogue/Helpers.h.
 *
 * include/rogue/Helpers.h defines `rogueStreamTap` and documents it with a
 * comment "// Add stream tap, DEPRECATED" but the macro itself carries no
 * compiler-visible deprecation attribute.  Downstream code that calls
 * `rogueStreamTap(...)` compiles silently without any diagnostic even with
 * `-Wall -Wdeprecated-declarations`.
 *
 * This test uses a source-text invariant (100% deterministic): reads
 * Helpers.h and asserts that (1) a [[deprecated]] attribute exists in the
 * file, and (2) the rogueStreamTap macro expansion references the
 * deprecated marker so call sites actually trigger the diagnostic.
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
#include <iterator>
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

TEST_CASE("rogueStreamTap actually triggers a compiler deprecation diagnostic") {
    // Read Helpers.h and verify two things:
    //   (1) the file declares a [[deprecated]] marker function
    //   (2) the rogueStreamTap macro expansion REFERENCES that marker, so a
    //       call site triggers a -Wdeprecated-declarations diagnostic.
    //
    // The original failure mode was a macro that simply expanded to
    // src->addSlave(dst) so callers got no compile-time warning despite the
    // adjacent "// DEPRECATED" comment.  A [[deprecated]] marker function
    // declared near the macro is necessary but not sufficient; the macro
    // must call the marker (or otherwise expand to deprecated-attributed
    // code) for the diagnostic to actually fire.

    const std::string src = readFile(std::string(ROGUE_SRC_DIR) + "/include/rogue/Helpers.h");

    REQUIRE_MESSAGE(!src.empty(),
                    "could not open include/rogue/Helpers.h (ROGUE_SRC_DIR=",
                    ROGUE_SRC_DIR, ")");

    // (1) A [[deprecated]] / __attribute__((deprecated)) attribute exists
    //     somewhere in the file (typically on a marker function).
    bool has_deprecated_attr =
        (src.find("[[deprecated")              != std::string::npos) ||
        (src.find("__attribute__((deprecated") != std::string::npos);
    CHECK_MESSAGE(has_deprecated_attr,
                  "Helpers.h has no [[deprecated]] or __attribute__((deprecated)) "
                  "anywhere; rogueStreamTap cannot trigger a compile diagnostic "
                  "without an attribute marker somewhere it can reach.");

    // (2) Locate the macro definition and verify it actually references a
    //     deprecated-attributed entity.  We look for the marker function
    //     name in the macro expansion; a bare expansion to ``src->addSlave``
    //     fails this check even if the marker is declared above.
    std::string tap_region = extractRegion(src, "#define rogueStreamTap", 200);
    REQUIRE_MESSAGE(!tap_region.empty(),
                    "could not locate #define rogueStreamTap in Helpers.h");

    bool macro_invokes_marker =
        (tap_region.find("rogueStreamTap_deprecated_notice_") != std::string::npos) ||
        (tap_region.find("ROGUE_DEPRECATED")                  != std::string::npos);

    CHECK_MESSAGE(macro_invokes_marker,
                  "rogueStreamTap macro does not reference a deprecated marker; "
                  "the macro expands directly to src->addSlave(dst) so callers "
                  "receive no compile-time diagnostic even if a [[deprecated]] "
                  "marker exists elsewhere in the file. Have the macro evaluate "
                  "the marker (e.g. ((void)(rogueStreamTap_deprecated_notice_(), "
                  "src->addSlave(dst)))).");
}
