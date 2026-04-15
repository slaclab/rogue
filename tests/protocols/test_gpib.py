#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import pytest

# pyrogue.protocols.gpib does ``from gpib_ctypes import Gpib`` at module
# level.  That package (pip install gpib-ctypes) wraps linux-gpib, which
# requires a physical GPIB interface and the linux-gpib kernel driver.
# Neither is present in CI or on most developer machines, so the import
# raises ImportError.  We skip the entire module gracefully — the same
# pattern used by test_pydm_rogue_plugin.py for optional Qt/PyDM deps.
try:
    from pyrogue.protocols.gpib import GpibController, GpibDevice  # noqa: F401
except Exception as exc:
    pytest.skip(
        f"GPIB dependencies unavailable: {exc}",
        allow_module_level=True,
    )


def test_gpib_controller_class_exists():
    assert GpibController is not None


def test_gpib_device_class_exists():
    assert GpibDevice is not None
