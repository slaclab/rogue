#!/bin/bash
# ----------------------------------------------------------------------------
# Title      : Rogue CMake dependency-block sync check
# ----------------------------------------------------------------------------
# CMakeLists.txt and templates/RogueConfig.cmake.in intentionally duplicate the
# dependency-discovery logic (Boost+Python, numpy, BZip2, ZeroMQ): the top-level
# file uses it to build rogue, and the installed RogueConfig.cmake re-runs it so
# downstream `find_package(Rogue)` consumers rediscover the same dependencies.
#
# The duplicated region is delimited in both files by:
#    # >>> ROGUE_DEPENDENCY_DISCOVERY ...
#    ...
#    # <<< ROGUE_DEPENDENCY_DISCOVERY
#
# This script extracts the lines strictly between those markers from each file
# and fails if they differ, so the two copies cannot silently drift apart.
#
# Invoked from scripts/run_linters.sh (Python and C++ Linters CI step). Run as
# `bash scripts/check_cmake_sync.sh` or `./scripts/check_cmake_sync.sh`.
# ----------------------------------------------------------------------------

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")
ROOT_DIR=$(cd "${SCRIPT_DIR}/.." && pwd)

FILE_A="${ROOT_DIR}/CMakeLists.txt"
FILE_B="${ROOT_DIR}/templates/RogueConfig.cmake.in"

BEGIN_MARKER="# >>> ROGUE_DEPENDENCY_DISCOVERY"
END_MARKER="# <<< ROGUE_DEPENDENCY_DISCOVERY"

WORK_DIR=$(mktemp -d)
trap 'rm -rf "${WORK_DIR}"' EXIT

# Extract the lines strictly between the begin and end markers into an output
# file. Returns non-zero unless exactly one begin marker and one end marker are
# present, in order. Writing to a file (rather than capturing via $(...))
# preserves trailing blank lines, which command substitution would strip.
extract_block() {
   local file="$1"
   local out="$2"
   awk -v b="${BEGIN_MARKER}" -v e="${END_MARKER}" '
      index($0, b) == 1 { if (in_block || begin_seen) { dup=1 } begin_seen++; in_block=1; next }
      index($0, e) == 1 { if (!in_block) { orphan=1 } end_seen++; in_block=0; next }
      in_block { print }
      END {
         if (begin_seen != 1 || end_seen != 1 || dup || orphan) {
            exit 2
         }
      }
   ' "$file" > "$out"
}

fail_markers() {
   local file="$1"
   echo "ERROR: ${file#"${ROOT_DIR}/"} must contain exactly one"
   echo "       '${BEGIN_MARKER}' ... '${END_MARKER}' marker pair (in order)."
   exit 1
}

extract_block "$FILE_A" "${WORK_DIR}/block_a" || fail_markers "$FILE_A"
extract_block "$FILE_B" "${WORK_DIR}/block_b" || fail_markers "$FILE_B"

if ! diff "${WORK_DIR}/block_a" "${WORK_DIR}/block_b" > "${WORK_DIR}/block_diff"; then
   echo "ERROR: the ROGUE_DEPENDENCY_DISCOVERY blocks have drifted out of sync."
   echo ""
   echo "  CMakeLists.txt and templates/RogueConfig.cmake.in must keep the lines"
   echo "  between the markers byte-identical. Mirror any edit into BOTH files."
   echo ""
   echo "  Diff (< CMakeLists.txt   > templates/RogueConfig.cmake.in):"
   echo ""
   cat "${WORK_DIR}/block_diff"
   exit 1
fi

echo "check_cmake_sync: ROGUE_DEPENDENCY_DISCOVERY blocks are in sync."
