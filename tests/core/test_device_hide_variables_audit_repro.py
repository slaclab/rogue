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

import inspect

import pyrogue as pr


def test_hide_variables_dict_values_index():
    """Device.hideVariables indexes variables[0] after dict_values assignment."""
    src = inspect.getsource(pr.Device.hideVariables)

    # When variables=None, the code sets variables = self.variables.values()
    # (a dict_values).  The elif then calls variables[0] which raises TypeError.
    # A correct implementation would either convert to list first or avoid
    # subscripting.  Assert the subscript is absent from the method body.
    assert "variables[0]" not in src, (
        "Device.hideVariables references variables[0] after assigning "
        "variables = self.variables.values() (dict_values); integer subscripting "
        "on dict_values raises TypeError — use list(variables)[0] or restructure "
        "the type check to not depend on subscripting"
    )
