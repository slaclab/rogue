#!/bin/bash
# ----------------------------------------------------------------------------
# Compiles scripts/probe_malloc_interposer.c into a preloadable shared object
# for the runner capability probe. Invoked from inside the probe job itself;
# the only input is the first-party C source committed to this repository,
# never a downloaded artifact or workflow input. Compilation can legitimately
# fail on a runner with an unexpected or missing toolchain (see
# scripts/ci_bring_up_soft_roce.sh for the established precedent of a probe
# step recording its own failure as a result rather than crashing); this
# script only reports the failure via its exit code, the caller decides
# whether that is fatal to the job.
#
# Usage: build_malloc_interposer.sh [OUTPUT_PATH] [SOURCE_PATH]
#   OUTPUT_PATH defaults to /tmp/probe_malloc_interposer.so
#   SOURCE_PATH defaults to the committed probe_malloc_interposer.c next to
#   this script; it is only ever overridden in tests exercising the failure
#   path, never in the probe workflow itself.
# ----------------------------------------------------------------------------

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")

OUTPUT_PATH="${1:-/tmp/probe_malloc_interposer.so}"
SOURCE_PATH="${2:-${SCRIPT_DIR}/probe_malloc_interposer.c}"

CC="${CC:-cc}"

echo "Compiler version: $("${CC}" --version | head -n1)"

COMPILE_CMD=("${CC}" -O2 -fPIC -shared -Wall -Wextra -o "${OUTPUT_PATH}" "${SOURCE_PATH}" -ldl)
echo "Compile command: ${COMPILE_CMD[*]}"
"${COMPILE_CMD[@]}"

echo "Built ${OUTPUT_PATH}"
