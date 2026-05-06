#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Regression test.
#   DataReceiver.__init__ has a mutable default argument
#   `value=numpy.zeros(shape=1, dtype=numpy.uint8, order='C')` (line 44).
#   The numpy array is created once at class-definition time.  All instances
#   that do not supply an explicit `value` argument share the same backing
#   array, so in-place mutation of the default in one instance leaks into
#   every other instance.
#   On HEAD `r1.Data.value() is r2.Data.value()` is True → mutation of the
#   first instance's array is visible in the second → the assertion FAILS.
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


def test_datareceiver_default_value_isolated():
    """DataReceiver mutable numpy default bleeds mutation across instances."""
    r1 = pr.DataReceiver(name='recv1')
    r2 = pr.DataReceiver(name='recv2')

    arr = r1.Data.value()
    arr[0] = 42

    r2_val = r2.Data.value()[0]

    assert r2_val == 0, (
        "DataReceiver mutable default leaked mutation across instances; "
        "r2.Data.value()[0] == " + str(r2_val) + " (expected 0); "
        "the numpy.zeros() array in the default argument is shared by all instances"
    )
