#!/bin/bash
# ----------------------------------------------------------------------------
# Sourced (not executed) from the Rogue test steps in
# .github/workflows/rogue_ci.yml. Sets shell options, raises memlock, and
# loads the Rogue build environment.
#
# -u is intentionally omitted: the sourced build/setup_rogue.sh expands
# ${PYQTDESIGNERPATH} without guarding against unset.
# ----------------------------------------------------------------------------

set -eo pipefail

# best-effort: GHA forbids raising RLIMIT_MEMLOCK without CAP_SYS_RESOURCE,
# and ibv_reg_mr is moot anyway when rxe0 cannot be brought up (see the
# `Bring up Soft-RoCE (rxe0)` step in .github/workflows/rogue_ci.yml). On a
# runner with a real Soft-RoCE device, /etc/security/limits.conf must permit
# memlock=unlimited.
ulimit -l unlimited 2>/dev/null || echo "ulimit -l unlimited denied (expected on GHA-hosted); continuing"

source build/setup_rogue.sh
