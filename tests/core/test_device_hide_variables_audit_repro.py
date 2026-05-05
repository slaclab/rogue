#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Regression test.
#   Device.hideVariables() assigns `variables = self.variables.values()` when
#   the caller passes `variables=None` (line 433).  The function then uses
#   `isinstance(variables[0], str)` inside the loop (line 438).
#   `dict_values` does not support integer indexing, so any code path that
#   reaches that elif with a dict_values object raises TypeError.
#   The test calls hideVariables with a list of string names (so the elif IS
#   reached) but where the local `variables` was first set to dict_values via
#   the None-default path.  A simpler, deterministic repro: assert that the
#   source code does not subscript `variables` after it may have been set to
#   a dict_values object.
#   On HEAD `variables[0]` is present → assertion fails.
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
    """Device.hideVariables(None) must not TypeError on dict_values subscripting.

    The original bug: ``variables = self.variables.values()`` when the caller
    passes ``variables=None``, followed by an integer subscript such as
    ``variables[0]``.  ``dict_values`` does not support integer indexing, so
    the call raises TypeError on every Device with at least one BaseVariable.

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
