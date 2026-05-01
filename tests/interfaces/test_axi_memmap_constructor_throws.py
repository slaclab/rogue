#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : AxiMemMap constructor throw paths
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
#
# Pin the AxiMemMap::AxiMemMap fd-cleanup contract added in this PR.
#
# AxiMemMap takes a path argument and opens it with O_RDWR, then calls
# dmaGetApiVersion() (an ioctl). Passing "/dev/null" makes ::open() succeed,
# and ioctl(fd, DMA_Get_Version, 0) on /dev/null fails with ENOTTY (-1). The
# signed compare ``-1 < 0x06`` is true, so the constructor enters the new
# fd-cleanup branch:
#
#   ::close(fd_);
#   fd_ = -1;
#   throw(...);
#
# Reverting the close-before-throw makes the fd count grow by one per
# iteration; the assertion below trips. /proc/self/fd is Linux-only.

import os
import sys

import pytest

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="/proc/self/fd is Linux-only",
)

try:
    import rogue.hardware.axi as axi
except Exception as exc:  # pragma: no cover - module unavailable on macOS
    pytest.skip(
        f"rogue.hardware.axi not available: {exc}",
        allow_module_level=True,
    )


def _open_fd_count() -> int:
    return len(os.listdir("/proc/self/fd"))


def test_axi_memmap_bad_driver_version_releases_fd():
    """A failed dmaGetApiVersion() check must close the fd before throwing.

    Reverting the close-before-throw added on this branch lets the per-call
    open() leak, and the fd count grows by one per iteration; the assertion
    catches it. The bound (+4) is slack for unrelated fd churn during the
    loop (logging, etc).
    """
    baseline = _open_fd_count()
    for _ in range(32):
        with pytest.raises(Exception, match="Bad kernel driver version"):
            axi.AxiMemMap("/dev/null")
    assert _open_fd_count() <= baseline + 4
