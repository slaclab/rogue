#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Regression test for Device.hideVariables() dict_values indexing bug.
#   The original code assigned `variables = self.variables.values()` when
#   the caller passed `variables=None`, then used `variables[0]` which fails
#   on dict_values. This test verifies the fix by calling hideVariables(True)
#   with the default variables=None and asserting it completes without error.
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import pyrogue as pr


def test_hide_variables_dict_values_index():
    """Device.hideVariables(True) with variables=None must not TypeError.

    The original bug: ``variables = self.variables.values()`` when the caller
    omits the ``variables`` kwarg (defaulting to None), followed by an integer
    subscript such as ``variables[0]``.  ``dict_values`` does not support
    integer indexing, so the call raises TypeError on every Device with at
    least one BaseVariable.

    Behavioural test: build a minimal Device with a single LocalVariable,
    invoke hideVariables(True) with the default variables=None, and verify
    that the call returns without raising.  A correct fix may either convert
    to list before subscripting, restructure the type check to iterate, or
    take any other shape that handles the dict_values default safely — the
    fix shape is unconstrained.
    """

    class _ProbeDevice(pr.Device):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.add(pr.LocalVariable(
                name='Probe',
                value=0,
                mode='RW',
            ))

    dev = _ProbeDevice(name='Probe')

    dev.hideVariables(True)
    assert dev.variables['Probe'].hidden is True

    dev.hideVariables(False)
    assert dev.variables['Probe'].hidden is False
