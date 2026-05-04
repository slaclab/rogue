#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Regression test.
#   pyrogue/__init__.py sets MIN_PYTHON = (3, 6) while CI and conda builds
#   only support Python 3.10-3.13; CPython 3.6 reached EOL December 2021.
#   Setting a 3.6 minimum allows users to install on unsupported interpreters
#   that lack f-strings, walrus operators, and many stdlib improvements used
#   throughout pyrogue.  On HEAD MIN_PYTHON = (3, 6) → assertion FAILS.
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import pyrogue


def test_min_python_at_least_310():
    """MIN_PYTHON = (3, 6) but conda matrix is 3.10-3.13; 3.6 EOL Dec 2021."""
    min_py = pyrogue.MIN_PYTHON

    assert min_py >= (3, 10), (
        "MIN_PYTHON = " + str(min_py) + " but conda build matrix "
        "targets 3.10-3.13 and CPython 3.6 reached end-of-life December 2021; "
        "the minimum version should be updated to at least (3, 10)"
    )
